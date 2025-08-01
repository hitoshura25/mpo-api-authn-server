package com.vmenon.mpo.authn.testclient

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * HTTP client for communicating with webauthn-test-service
 */
class TestServiceClient(private val baseUrl: String = "http://10.0.2.2:8081") {

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    /**
     * Generate a test registration credential
     */
    suspend fun generateRegistrationCredential(request: TestRegistrationRequest): TestCredentialResponse =
        withContext(Dispatchers.IO) {
            val requestBody = gson.toJson(request).toRequestBody(jsonMediaType)

            val httpRequest = Request.Builder()
                .url("$baseUrl/test/generate-registration-credential")
                .post(requestBody)
                .build()

            val response = httpClient.newCall(httpRequest).execute()

            if (!response.isSuccessful) {
                throw Exception("Failed to generate registration credential: ${response.code} ${response.message}")
            }

            val responseBody = response.body?.string() ?: throw Exception("Empty response body")
            gson.fromJson(responseBody, TestCredentialResponse::class.java)
        }

    /**
     * Generate a test authentication credential
     */
    suspend fun generateAuthenticationCredential(request: TestAuthenticationRequest): TestCredentialResponse =
        withContext(Dispatchers.IO) {
            val requestBody = gson.toJson(request).toRequestBody(jsonMediaType)

            val httpRequest = Request.Builder()
                .url("$baseUrl/test/generate-authentication-credential")
                .post(requestBody)
                .build()

            val response = httpClient.newCall(httpRequest).execute()

            if (!response.isSuccessful) {
                throw Exception("Failed to generate authentication credential: ${response.code} ${response.message}")
            }

            val responseBody = response.body?.string() ?: throw Exception("Empty response body")
            gson.fromJson(responseBody, TestCredentialResponse::class.java)
        }

    /**
     * Check test service health
     */
    suspend fun checkHealth(): TestServiceHealthResponse = withContext(Dispatchers.IO) {
        val httpRequest = Request.Builder()
            .url("$baseUrl/health")
            .get()
            .build()

        val response = httpClient.newCall(httpRequest).execute()

        if (!response.isSuccessful) {
            throw Exception("Test service health check failed: ${response.code} ${response.message}")
        }

        val responseBody = response.body?.string() ?: throw Exception("Empty response body")
        gson.fromJson(responseBody, TestServiceHealthResponse::class.java)
    }

    /**
     * Clear test service data
     */
    suspend fun clearTestData(): String = withContext(Dispatchers.IO) {
        val httpRequest = Request.Builder()
            .url("$baseUrl/test/clear")
            .post("".toRequestBody(jsonMediaType))
            .build()

        val response = httpClient.newCall(httpRequest).execute()

        if (!response.isSuccessful) {
            throw Exception("Failed to clear test data: ${response.code} ${response.message}")
        }

        response.body?.string() ?: "Success"
    }
}