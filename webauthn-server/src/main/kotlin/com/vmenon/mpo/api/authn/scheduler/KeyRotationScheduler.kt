package com.vmenon.mpo.api.authn.scheduler

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
     * The scheduler checks for rotation every hour in production mode.
     * In test mode (with rotation interval < 2 minutes), it checks more frequently.
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
                // Check interval: 1 hour in production, more frequent in test mode
                val checkInterval = determineCheckInterval()

                logger.info("Key rotation scheduler started. Check interval: {}ms", checkInterval.toMillis())

                while (isActive) {
                    try {
                        keyRotationService.checkAndRotateIfNeeded()
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
     * Determine the check interval based on configuration.
     *
     * In test mode (rotation interval < 120 seconds), check every 10 seconds.
     * In production mode, check every hour.
     *
     * @return Duration between rotation checks
     */
    private fun determineCheckInterval(): Duration {
        val rotationIntervalSeconds =
            (System.getProperty("MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS")
                ?: System.getenv("MPO_AUTHN_JWT_ROTATION_INTERVAL_SECONDS"))?.toLongOrNull()

        return if (rotationIntervalSeconds != null && rotationIntervalSeconds < 120) {
            // Test mode: Check every 10 seconds
            Duration.ofSeconds(10)
        } else {
            // Production mode: Check every hour
            Duration.ofHours(1)
        }
    }
}
