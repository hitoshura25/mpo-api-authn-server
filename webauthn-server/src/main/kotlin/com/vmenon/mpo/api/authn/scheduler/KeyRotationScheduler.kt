package com.vmenon.mpo.api.authn.scheduler

import com.typesafe.config.ConfigFactory
import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.security.KeyRotationService
import org.slf4j.LoggerFactory
import kotlinx.coroutines.*
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

                logger.info("Key rotation scheduler started. Check interval: {}ms", checkInterval.toMillis())

                while (isActive) {
                    try {
                        // Check if rotation is needed (based on key age)
                        keyRotationService.checkAndRotateIfNeeded()

                        // Check if any PENDING keys should be activated (after grace period)
                        keyRotationService.checkAndActivatePendingKeys()
                    } catch (e: Exception) {
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

        return try {
            val config = ConfigFactory.parseString("temp = $rotationIntervalValue")
            val rotationInterval = config.getDuration("temp")

            when {
                rotationInterval < Duration.ofMinutes(5) -> {
                    // Fast rotation: Check every 10 seconds
                    Duration.ofSeconds(10)
                }
                rotationInterval < Duration.ofDays(1) -> {
                    // Medium rotation: Check every minute
                    Duration.ofMinutes(1)
                }
                else -> {
                    // Slow rotation: Check every hour
                    Duration.ofHours(1)
                }
            }
        } catch (e: Exception) {
            logger.warn(
                "Failed to parse rotation interval '{}', defaulting to 1 hour check interval",
                rotationIntervalValue,
                e
            )
            Duration.ofHours(1)
        }
    }
}
