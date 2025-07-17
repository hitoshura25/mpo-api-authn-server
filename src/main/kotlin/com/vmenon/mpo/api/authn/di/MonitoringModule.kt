package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import io.micrometer.prometheus.PrometheusConfig
import io.micrometer.prometheus.PrometheusMeterRegistry
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.api.trace.Tracer
import io.opentelemetry.context.propagation.ContextPropagators
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter
import io.opentelemetry.extension.trace.propagation.JaegerPropagator
import io.opentelemetry.sdk.OpenTelemetrySdk
import io.opentelemetry.sdk.resources.Resource
import io.opentelemetry.sdk.trace.SdkTracerProvider
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor
import io.opentelemetry.semconv.ServiceAttributes
import java.util.Optional
import org.koin.core.qualifier.named
import org.koin.dsl.module

val monitoringModule = module {
    single(named("openTelemetryServiceName")) {
        val value = System.getProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME) ?: "MPO-API-AUTHN"
        require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME} cannot be blank" }
        value
    }

    single<Optional<String>>(named("openTelemetryJaegerEndpoint")) {
        val value: String? = System.getProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT)
            ?: System.getenv(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT)
        if (value != null) {
            require(value.isNotBlank()) { "${EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT} cannot be blank" }
        }
        Optional.ofNullable(value)
    }

    single<OpenTelemetry> {
        val jaegerEndpoint: Optional<String> by inject(named("openTelemetryJaegerEndpoint"))
        if (jaegerEndpoint.isPresent) {
            val endpoint = jaegerEndpoint.get()
            logger.info("Using Jaeger endpoint: $endpoint")
            val serviceName: String by inject(named("openTelemetryServiceName"))
            val resource = Resource.getDefault()
                .merge(
                    Resource.builder()
                        .put(ServiceAttributes.SERVICE_NAME, serviceName)
                        .put(ServiceAttributes.SERVICE_VERSION, "1.0.0")
                        .build()
                )

            val jaegerExporter = OtlpGrpcSpanExporter.builder()
                .setEndpoint(endpoint)
                .build()

            val tracerProvider = SdkTracerProvider.builder()
                .addSpanProcessor(BatchSpanProcessor.builder(jaegerExporter).build())
                .setResource(resource)
                .build()

            OpenTelemetrySdk.builder()
                .setTracerProvider(tracerProvider)
                .setPropagators(ContextPropagators.create(JaegerPropagator.getInstance()))
                .build()
        } else {
            OpenTelemetry.noop()
        }
    }

    single<Tracer> {
        val openTelemetry: OpenTelemetry by inject()
        val serviceName: String by inject(named("openTelemetryServiceName"))
        openTelemetry.getTracer(serviceName)
    }

    single<PrometheusMeterRegistry> {
        PrometheusMeterRegistry(PrometheusConfig.DEFAULT)
    }
}