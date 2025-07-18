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
import com.vmenon.mpo.api.authn.routes.configureRegistrationRoutes
import com.vmenon.mpo.api.authn.storage.AssertionRequestStorage
import com.vmenon.mpo.api.authn.storage.CredentialStorage
import com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage
import io.ktor.server.application.Application
import io.ktor.server.application.ApplicationStopping
import io.ktor.server.application.install
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import org.koin.core.module.Module
import org.koin.ktor.ext.inject
import org.koin.ktor.plugin.Koin
import org.koin.logger.slf4jLogger

fun Application.module(storageModule: Module) {
    configureDependencyInjection(storageModule)
    configurePlugins()
    configureRouting()
    configureLifecycle()
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
}

private fun Application.configureRouting() {
    configureHealthRoutes()
    configureRegistrationRoutes()
    configureAuthenticationRoutes()
}

private fun Application.configureLifecycle() {
    val credentialStorage: CredentialStorage by inject()
    val registrationStorage: RegistrationRequestStorage by inject()
    val assertionStorage: AssertionRequestStorage by inject()

    environment.monitor.subscribe(ApplicationStopping) {
        credentialStorage.close()
        registrationStorage.close()
        assertionStorage.close()
    }
}

fun main() {
    embeddedServer(Netty, port = 8080) {
        module(storageModule)
    }.start(wait = true)
}
