package com.vmenon.mpo.api.authn.scheduler

import com.typesafe.config.ConfigFactory
import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.security.KeyRotationService
import org.slf4j.LoggerFactory
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.time.Duration

/**
 * Background scheduler for automatic JWT key rotation.
 *
 * Periodically checks if key rotation is needed and triggers rotation when appropriate.
 * Also handles cleanup of expired RETIRED keys.
 *
 * The scheduler runs in a separate coroutine and can be started/stopped independently
 * of the main application lifecycle.
 *
 * @property keyRotationService The key rotation service to use for rotation operations
 */
class KeyRotationScheduler(
    private val keyRotationService: KeyRotationService,
) {
    private val logger = LoggerFactory.getLogger(KeyRotationScheduler::class.java)
    private var job: Job? = null

    private companion object {
        // Check interval thresholds for adaptive scheduling
        const val FAST_ROTATION_CHECK_INTERVAL_SECONDS = 10L
        const val MEDIUM_ROTATION_CHECK_INTERVAL_MINUTES = 1L
        const val SLOW_ROTATION_CHECK_INTERVAL_HOURS = 1L

        // Rotation speed thresholds (in minutes)
        const val FAST_ROTATION_THRESHOLD_MINUTES = 5L

        // Duration formatting thresholds
        const val SECONDS_PER_MINUTE = 60L
        const val SECONDS_PER_HOUR = 3600L
        const val SECONDS_PER_DAY = 86400L
    }

    /**
     * Start the background scheduler.
     *
     * The scheduler performs two operations periodically:
     * 1. Check if rotation is needed (based on key age vs rotation interval)
     * 2. Activate PENDING keys that have exceeded grace period
     *
     * Check interval is adaptive based on rotation speed to ensure timely activation.
     *
     * This method is idempotent - calling it multiple times has no effect if already running.
     */
    fun start() {
        if (job != null && job?.isActive == true) {
            logger.warn("Key rotation scheduler is already running")
            return
        }

        job =
            CoroutineScope(Dispatchers.IO).launch {
                val checkInterval = determineCheckInterval()

                logger.info("Key rotation scheduler started. Check interval: {}", formatDuration(checkInterval))

                while (isActive) {
                    runCatching {
                        // Check if rotation is needed (based on key age)
                        keyRotationService.checkAndRotateIfNeeded()

                        // Check if any PENDING keys should be activated (after grace period)
                        keyRotationService.checkAndActivatePendingKeys()
                    }.onFailure { e ->
                        logger.error("Error during key rotation check", e)
                    }

                    delay(checkInterval.toMillis())
                }
            }
    }

    /**
     * Stop the background scheduler.
     *
     * This method is idempotent - calling it multiple times has no effect if not running.
     */
    fun stop() {
        job?.cancel()
        job = null
        logger.info("Key rotation scheduler stopped")
    }

    /**
     * Determine the check interval based on rotation configuration.
     *
     * Universal adaptive approach that works for all rotation speeds:
     * - Fast rotation (< 5 min): Check every 10 seconds
     * - Medium rotation (5 min - 1 day): Check every 1 minute
     * - Slow rotation (> 1 day): Check every 1 hour
     *
     * This ensures timely activation of PENDING keys without excessive checking.
     *
     * @return Duration between rotation checks
     */
    private fun determineCheckInterval(): Duration {
        val rotationIntervalValue =
            System.getProperty(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
                ?: System.getenv(EnvironmentVariables.MPO_AUTHN_JWT_KEY_ROTATION_INTERVAL)
                ?: "180d"

        return runCatching {
            val config = ConfigFactory.parseString("temp = $rotationIntervalValue")
            val rotationInterval = config.getDuration("temp")

            when {
                rotationInterval < Duration.ofMinutes(FAST_ROTATION_THRESHOLD_MINUTES) -> {
                    // Fast rotation: Check every 10 seconds
                    Duration.ofSeconds(FAST_ROTATION_CHECK_INTERVAL_SECONDS)
                }
                rotationInterval < Duration.ofDays(1) -> {
                    // Medium rotation: Check every minute
                    Duration.ofMinutes(MEDIUM_ROTATION_CHECK_INTERVAL_MINUTES)
                }
                else -> {
                    // Slow rotation: Check every hour
                    Duration.ofHours(SLOW_ROTATION_CHECK_INTERVAL_HOURS)
                }
            }
        }.getOrElse { e ->
            logger.warn(
                "Failed to parse rotation interval '{}', defaulting to 1 hour check interval",
                rotationIntervalValue,
                e
            )
            Duration.ofHours(SLOW_ROTATION_CHECK_INTERVAL_HOURS)
        }
    }

    /**
     * Format duration in human-readable format for logging.
     * Examples: "10s", "1m", "1h", "1d"
     */
    private fun formatDuration(duration: Duration): String {
        val seconds = duration.seconds
        return when {
            seconds < SECONDS_PER_MINUTE -> "${seconds}s"
            seconds < SECONDS_PER_HOUR -> "${seconds / SECONDS_PER_MINUTE}m"
            seconds < SECONDS_PER_DAY -> "${seconds / SECONDS_PER_HOUR}h"
            else -> "${seconds / SECONDS_PER_DAY}d"
        }
    }
}
