package com.vmenon.mpo.api.authn.routes

import com.vmenon.mpo.api.authn.RegistrationCompleteRequest
import com.vmenon.mpo.api.authn.RegistrationRequest
import com.vmenon.mpo.api.authn.RegistrationResponse
import com.vmenon.mpo.api.authn.monitoring.OpenTelemetryTracer
import com.vmenon.mpo.api.authn.storage.CredentialRegistration
import com.vmenon.mpo.api.authn.storage.UserAccount
import com.yubico.webauthn.FinishRegistrationOptions
import com.yubico.webauthn.RegisteredCredential
import com.yubico.webauthn.RelyingParty
import com.yubico.webauthn.StartRegistrationOptions
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import com.yubico.webauthn.data.UserIdentity
import java.util.Base64
import java.util.UUID

object RegistrationUtils {
    suspend fun createRegistrationResponse(
        request: RegistrationRequest,
        requestId: String,
        relyingParty: RelyingParty,
        registrationStorage: com.vmenon.mpo.api.authn.storage.RegistrationRequestStorage,
        openTelemetryTracer: OpenTelemetryTracer,
    ): RegistrationResponse {
        val userHandle = ByteArray.fromBase64Url(
            Base64.getUrlEncoder().withoutPadding()
                .encodeToString(UUID.randomUUID().toString().toByteArray()),
        )

        val user = openTelemetryTracer.traceOperation("buildUserIdentity") {
            UserIdentity.builder()
                .name(request.username)
                .displayName(request.displayName)
                .id(userHandle)
                .build()
        }

        val startRegistrationOptions = openTelemetryTracer.traceOperation("relyingParty.startRegistration") {
            relyingParty.startRegistration(
                StartRegistrationOptions.builder()
                    .user(user)
                    .build(),
            )
        }

        registrationStorage.storeRegistrationRequest(requestId, startRegistrationOptions)

        val credentialsJson = openTelemetryTracer.traceOperation("toCredentialsCreateJson") {
            startRegistrationOptions.toCredentialsCreateJson()
        }
        val credentialsObject = openTelemetryTracer.readTree(credentialsJson)

        return RegistrationResponse(
            requestId = requestId,
            publicKeyCredentialCreationOptions = credentialsObject,
        )
    }

    fun processRegistrationFinish(
        startRegistrationOptions: PublicKeyCredentialCreationOptions,
        request: RegistrationCompleteRequest,
        relyingParty: RelyingParty,
    ) = relyingParty.finishRegistration(
        FinishRegistrationOptions.builder()
            .request(startRegistrationOptions)
            .response(PublicKeyCredential.parseRegistrationResponseJson(request.credential))
            .build(),
    )

    fun createUserAccount(startRegistrationOptions: PublicKeyCredentialCreationOptions) =
        UserAccount(
            username = startRegistrationOptions.user.name,
            displayName = startRegistrationOptions.user.displayName,
            userHandle = startRegistrationOptions.user.id,
        )

    fun createCredentialRegistration(
        userAccount: UserAccount,
        finishRegistrationResult: com.yubico.webauthn.RegistrationResult,
    ) = CredentialRegistration(
        userAccount = userAccount,
        credential = RegisteredCredential.builder()
            .credentialId(finishRegistrationResult.keyId.id)
            .userHandle(userAccount.userHandle)
            .publicKeyCose(finishRegistrationResult.publicKeyCose)
            .signatureCount(finishRegistrationResult.signatureCount)
            .build(),
    )
}
