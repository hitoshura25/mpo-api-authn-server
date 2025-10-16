package com.vmenon.mpo.api.authn

import com.vmenon.mpo.api.authn.di.appModule
import com.vmenon.mpo.api.authn.di.monitoringModule
import com.vmenon.mpo.api.authn.di.storageModule
import com.vmenon.mpo.api.authn.plugins.configureCORS
import com.vmenon.mpo.api.authn.plugins.configureLogging
import com.vmenon.mpo.api.authn.plugins.configureMetrics
import com.vmenon.mpo.api.authn.plugins.configureOpenTelemetry
import com.vmenon.mpo.api.authn.plugins.configureSerialization
import com.vmenon.mpo.api.authn.plugins.configureStatusPages
import com.vmenon.mpo.api.authn.routes.configureAuthenticationRoutes
import com.vmenon.mpo.api.authn.routes.configureHealthRoutes
import com.vmenon.mpo.api.authn.routes.configureOpenAPIRoutes
import com.vmenon.mpo.api.authn.routes.configureRegistrationRoutes
import io.ktor.server.application.Application
import io.ktor.server.application.install
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import org.koin.core.module.Module
import org.koin.ktor.plugin.Koin
import org.koin.logger.slf4jLogger
import org.slf4j.LoggerFactory

const val PORT = 8080

fun Application.module(storageModule: Module) {
    configureDependencyInjection(storageModule)
    configurePlugins()
    configureRouting()
}

private fun Application.configureDependencyInjection(storageModule: Module) {
    install(Koin) {
        slf4jLogger()
        modules(listOf(appModule, storageModule, monitoringModule))
    }
}

private fun Application.configurePlugins() {
    configureSerialization()
    configureCORS()
    configureStatusPages()
    configureMetrics()
    configureLogging()
    configureOpenTelemetry()
    configureOpenAPIRoutes()
}

private fun Application.configureRouting() {
    configureHealthRoutes()
    configureRegistrationRoutes()
    configureAuthenticationRoutes()
}

fun main() {
    val logger = LoggerFactory.getLogger("com.vmenon.mpo.api.authn.Application")

    logger.info("========================================")
    logger.info("MPO WebAuthn Server Starting")
    logger.info("Port: $PORT")
    logger.info("WebAuthn Version: 2.0/FIDO2")
    logger.info("========================================")

    embeddedServer(Netty, port = PORT) {
        module(storageModule)
    }.start(wait = true)
}
