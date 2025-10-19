package com.vmenon.mpo.api.authn.di

import com.vmenon.mpo.api.authn.config.EnvironmentVariables
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import io.micrometer.prometheus.PrometheusConfig
import io.micrometer.prometheus.PrometheusMeterRegistry
import io.opentelemetry.api.GlobalOpenTelemetry
import io.opentelemetry.api.OpenTelemetry
import io.opentelemetry.api.trace.Tracer
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator
import io.opentelemetry.context.propagation.ContextPropagators
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter
import io.opentelemetry.sdk.OpenTelemetrySdk
import io.opentelemetry.sdk.resources.Resource
import io.opentelemetry.sdk.trace.SdkTracerProvider
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor
import io.opentelemetry.semconv.ServiceAttributes
import org.koin.core.qualifier.named
import org.koin.dsl.module
import java.util.Optional

val monitoringModule =
    module {
        single(named("openTelemetryServiceName")) {
            val value =
                System.getProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME)
                    ?: System.getenv(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME)
                    ?: "MPO-API-AUTHN"
            require(value.isNotBlank()) {
                "${EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_SERVICE_NAME} cannot be blank"
            }
            value
        }

        single<Optional<String>>(named("openTelemetryJaegerEndpoint")) {
            val value: String? =
                System.getProperty(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT)
                    ?: System.getenv(EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT)
            if (value != null) {
                require(value.isNotBlank()) {
                    "${EnvironmentVariables.MPO_AUTHN_OPEN_TELEMETRY_JAEGER_ENDPOINT} " +
                        "cannot be blank"
                }
            }
            Optional.ofNullable(value)
        }

        single<OpenTelemetry> {
            val jaegerEndpoint: Optional<String> by inject(named("openTelemetryJaegerEndpoint"))

            // Control global OpenTelemetry registration via system property
            val isGlobalOpenTelemetryEnabled = System.getProperty("otel.global.disabled") != "true"

            if (jaegerEndpoint.isPresent) {
                val endpoint = jaegerEndpoint.get()
                logger.info("Using Jaeger endpoint: $endpoint")
                val serviceName: String by inject(named("openTelemetryServiceName"))
                val resource =
                    Resource.getDefault()
                        .merge(
                            Resource.builder()
                                .put(ServiceAttributes.SERVICE_NAME, serviceName)
                                .put(ServiceAttributes.SERVICE_VERSION, "1.0.0")
                                .build(),
                        )

                val jaegerExporter =
                    OtlpGrpcSpanExporter.builder()
                        .setEndpoint(endpoint)
                        .build()

                val tracerProvider =
                    SdkTracerProvider.builder()
                        .addSpanProcessor(BatchSpanProcessor.builder(jaegerExporter).build())
                        .setResource(resource)
                        .build()

                val openTelemetrySdk =
                    OpenTelemetrySdk.builder()
                        .setTracerProvider(tracerProvider)
                        .setPropagators(
                            ContextPropagators.create(W3CTraceContextPropagator.getInstance()),
                        )
                        .build()

                if (isGlobalOpenTelemetryEnabled) {
                    // Production: Register globally for automatic context propagation
                    GlobalOpenTelemetry.set(openTelemetrySdk)
                    openTelemetrySdk
                } else {
                    // Tests: Build without global registration (prevents race conditions)
                    logger.info("Global OpenTelemetry registration disabled for testing")
                    openTelemetrySdk
                }
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

        single<OpenTelemetryTracer> {
            val tracer: Tracer by inject()
            OpenTelemetryTracer(tracer)
        }
    }
