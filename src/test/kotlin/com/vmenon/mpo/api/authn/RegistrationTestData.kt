package com.vmenon.mpo.api.authn

import com.yubico.webauthn.data.AttestationObject
import com.yubico.webauthn.data.AuthenticatorAttestationResponse
import com.yubico.webauthn.data.AuthenticatorSelectionCriteria
import com.yubico.webauthn.data.AuthenticatorTransport
import com.yubico.webauthn.data.ByteArray
import com.yubico.webauthn.data.COSEAlgorithmIdentifier
import com.yubico.webauthn.data.ClientRegistrationExtensionOutputs
import com.yubico.webauthn.data.PublicKeyCredential
import com.yubico.webauthn.data.PublicKeyCredentialCreationOptions
import com.yubico.webauthn.data.RegistrationExtensionInputs
import com.yubico.webauthn.data.RelyingPartyIdentity
import com.yubico.webauthn.data.UserIdentity
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.security.KeyFactory
import java.security.PrivateKey
import java.security.cert.CertificateException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.spec.PKCS8EncodedKeySpec
import java.util.Base64

// Taken from the tests in Yubico's java-webauthn-server: https://github.com/Yubico/java-webauthn-server/blob/365aba221da3a64fa0ee788a1878cf4d737f4b2b/webauthn-server-core/src/test/scala/com/yubico/webauthn/RegistrationTestData.scala
object FidoU2F {
    fun basicAttestation(challenge: String) = RegistrationTestData(
        challenge = challenge,
        alg = COSEAlgorithmIdentifier.ES256,
        attestationObject =
            ByteArray.fromHex(
                "bf68617574684461746158a449960de5880e8c687434170f6476605b8fe4aeb9a28632c7995cf3ba831d97634100000539000102030405060708090a0b0c0d0e0f00206c6bce2ee5169934d2d590abb976db458c0dcfcd9d82360fbc93c268668b56a6a5010203262001215820171d8294528e18ebcec47f0426f5aa9dcb4c8b7ab7d38609baf333c41c4d2c852258209d653007939949f6daee042081d6434a50d7eb8a4fafd142cc8189435b6a9f1563666d74686669646f2d7532666761747453746d74bf63783563815901ea308201e63082018ca0030201020202269d300a06082a8648ce3d040302306a3126302406035504030c1d59756269636f20576562417574686e20756e6974207465737473204341310f300d060355040a0c0659756269636f31223020060355040b0c1941757468656e74696361746f72204174746573746174696f6e310b3009060355040613025345301e170d3138303930363137343230305a170d3138303931333137343230305a30673123302106035504030c1a59756269636f20576562417574686e20756e6974207465737473310f300d060355040a0c0659756269636f31223020060355040b0c1941757468656e74696361746f72204174746573746174696f6e310b30090603550406130253453059301306072a8648ce3d020106082a8648ce3d03010703420004ea588dd17cbc7f702116e53a1caf6f40b51b30c89536bdcbe8ce70cd3c78dc61198ebeff86c5f012d57921c39f9b80342109c7a30c63bd341b15ad32076853bca32530233021060b2b0601040182e51c01010404120410000102030405060708090a0b0c0d0e0f300a06082a8648ce3d040302034800304502210091d462574131dd530219334938561c4a752c0177c7ff9e85af455248aca2debc02204ea8005deafd97acab96f509751f45ff12b57640162880dc6f7fa18ae44883d863736967584730450220362d1f5e267509d28401a6e9762c3d6ef22116c7f8e267cab9c5eb2ddb78673f022100bf8fc4e079570315669cf7580ea18ecc7bc15cd66125073c1d68f8ca220dc238ffff"
            ),
        privateKey = ByteArray.fromHex("308193020100301306072a8648ce3d020106082a8648ce3d0301070479307702010104209c979b0f5035b44f2ac7ed29d4d20cc127895fbba82b69b0311dea9b2e57e8dea00a06082a8648ce3d030107a14403420004171d8294528e18ebcec47f0426f5aa9dcb4c8b7ab7d38609baf333c41c4d2c859d653007939949f6daee042081d6434a50d7eb8a4fafd142cc8189435b6a9f15"),
        attestationCertChain = listOf(
            importAttestationCa(
                "MIIB5jCCAYygAwIBAgICJp0wCgYIKoZIzj0EAwIwajEmMCQGA1UEAwwdWXViaWNvIFdlYkF1dGhuIHVuaXQgdGVzdHMgQ0ExDzANBgNVBAoMBll1YmljbzEiMCAGA1UECwwZQXV0aGVudGljYXRvciBBdHRlc3RhdGlvbjELMAkGA1UEBhMCU0UwHhcNMTgwOTA2MTc0MjAwWhcNMTgwOTEzMTc0MjAwWjBnMSMwIQYDVQQDDBpZdWJpY28gV2ViQXV0aG4gdW5pdCB0ZXN0czEPMA0GA1UECgwGWXViaWNvMSIwIAYDVQQLDBlBdXRoZW50aWNhdG9yIEF0dGVzdGF0aW9uMQswCQYDVQQGEwJTRTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABOpYjdF8vH9wIRblOhyvb0C1GzDIlTa9y+jOcM08eNxhGY6+/4bF8BLVeSHDn5uANCEJx6MMY700GxWtMgdoU7yjJTAjMCEGCysGAQQBguUcAQEEBBIEEAABAgMEBQYHCAkKCwwNDg8wCgYIKoZIzj0EAwIDSAAwRQIhAJHUYldBMd1TAhkzSThWHEp1LAF3x/+eha9FUkisot68AiBOqABd6v2XrKuW9Ql1H0X/ErV2QBYogNxvf6GK5EiD2A==",
                "EC",
                "MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgfMvSYwJCO1Mu7owbFmLYt9lQ2H8zqFoD4+kqeiybvnmgCgYIKoZIzj0DAQehRANCAATqWI3RfLx/cCEW5Tocr29AtRswyJU2vcvoznDNPHjcYRmOvv+GxfAS1Xkhw5+bgDQhCcejDGO9NBsVrTIHaFO8",
            ),
            importAttestationCa(
                "MIIB1zCCAX2gAwIBAgICJTwwCgYIKoZIzj0EAwIwajEmMCQGA1UEAwwdWXViaWNvIFdlYkF1dGhuIHVuaXQgdGVzdHMgQ0ExDzANBgNVBAoMBll1YmljbzEiMCAGA1UECwwZQXV0aGVudGljYXRvciBBdHRlc3RhdGlvbjELMAkGA1UEBhMCU0UwHhcNMTgwOTA2MTc0MjAwWhcNMTgwOTEzMTc0MjAwWjBqMSYwJAYDVQQDDB1ZdWJpY28gV2ViQXV0aG4gdW5pdCB0ZXN0cyBDQTEPMA0GA1UECgwGWXViaWNvMSIwIAYDVQQLDBlBdXRoZW50aWNhdG9yIEF0dGVzdGF0aW9uMQswCQYDVQQGEwJTRTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABB+mZAZb/g/+MPZiqGJw3BJ05x6Ku/Hqs3Po6dOVkUhcVUTMviUrKWcLY2m6/fAuEKNmrMc1nIs7HMryxYQK4C+jEzARMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIhAPfhXdfTbgSsg9qNz/s1pPUZumWW7rgG790HGsL5o2H9AiAJiLmlnBZNR1hS1dNYXBOJorEWXUq3rMF0EjCh7sD8aw==",
                "EC",
                "MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg712jkzFvwyWNpRxBkG/bao9vp2rHkHnYJl7V4Sz1SV2gCgYIKoZIzj0DAQehRANCAAQfpmQGW/4P/jD2YqhicNwSdOceirvx6rNz6OnTlZFIXFVEzL4lKylnC2Npuv3wLhCjZqzHNZyLOxzK8sWECuAv",
            ),
        ),
        transports = setOf(AuthenticatorTransport.USB),
    )
}

private val BASE64_DECODER: Base64.Decoder = Base64.getDecoder()
private val FIXSIG = listOf(
    "CN=Yubico U2F EE Serial 776137165",
    "CN=Yubico U2F EE Serial 1086591525",
    "CN=Yubico U2F EE Serial 1973679733",
    "CN=Yubico U2F EE Serial 13503277888",
    "CN=Yubico U2F EE Serial 13831167861",
    "CN=Yubico U2F EE Serial 14803321578"
)
private const val UNUSED_BITS_BYTE_INDEX_FROM_END = 257

@Throws(CertificateException::class)
fun parseDer(base64DerEncodedCert: String?): X509Certificate {
    return parseDer(BASE64_DECODER.decode(base64DerEncodedCert))
}

@Throws(CertificateException::class)
fun parseDer(`is`: InputStream?): X509Certificate {
    var cert =
        CertificateFactory.getInstance("X.509").generateCertificate(`is`) as X509Certificate
    // Some known certs have an incorrect "unused bits" value, which causes problems on newer
    // versions of BouncyCastle.
    if (FIXSIG.contains(cert.getSubjectX500Principal().name)) {
        val encoded = cert.encoded
        if (encoded.size >= UNUSED_BITS_BYTE_INDEX_FROM_END) {
            encoded[encoded.size - UNUSED_BITS_BYTE_INDEX_FROM_END] =
                0 // Fix the "unused bits" field (should always be 0).
        } else {
            throw IllegalArgumentException(
                java.lang.String.format(
                    "Expected DER encoded cert to be at least %d bytes, was %d: %s",
                    UNUSED_BITS_BYTE_INDEX_FROM_END, encoded.size, cert
                )
            )
        }

        cert =
            CertificateFactory.getInstance("X.509")
                .generateCertificate(ByteArrayInputStream(encoded)) as X509Certificate
    }
    return cert
}

@Throws(CertificateException::class)
fun parseDer(derEncodedCert: kotlin.ByteArray): X509Certificate {
    return parseDer(ByteArrayInputStream(derEncodedCert))
}

@Throws(CertificateException::class)
private fun parsePem(pemEncodedCert: String): X509Certificate {
    return parseDer(
        pemEncodedCert
            .replace("-----BEGIN CERTIFICATE-----".toRegex(), "")
            .replace("-----END CERTIFICATE-----".toRegex(), "")
            .replace("\n".toRegex(), "")
    )
}

private fun importAttestationCa(
    certBase64: String,
    keyAlgorithm: String,
    keyBase64: String,
): Pair<X509Certificate, PrivateKey> {
    val cert: X509Certificate = parsePem(certBase64)

    val kf = KeyFactory.getInstance(keyAlgorithm)
    val key: PrivateKey = kf.generatePrivate(
        PKCS8EncodedKeySpec(ByteArray.fromBase64(keyBase64).bytes)
    )

    return Pair(cert, key)
}

data class RegistrationTestData(
    val alg: COSEAlgorithmIdentifier,
    val attestationObject: ByteArray,
    val attestationCertChain: List<Pair<X509Certificate, PrivateKey>> = emptyList(),
    val attestationRootCertificate: X509Certificate? = null,
    val challenge: String,
    val authenticatorSelection: AuthenticatorSelectionCriteria? = null,
    val clientExtensionResults: ClientRegistrationExtensionOutputs =
        ClientRegistrationExtensionOutputs.builder().build(),
    val privateKey: ByteArray? = null,
    val overrideRequest: PublicKeyCredentialCreationOptions? = null,
    val requestedExtensions: RegistrationExtensionInputs =
        RegistrationExtensionInputs.builder().build(),
    val rpId: RelyingPartyIdentity =
        RelyingPartyIdentity.builder().id("localhost").name("Test party").build(),
    val userId: UserIdentity = UserIdentity
        .builder()
        .name("test@test.org")
        .displayName("Test user")
        .id(ByteArray(ByteArray(3) {
            when (it) {
                0 -> 42; 1 -> 13; else -> 37
            }
        }))
        .build(),
    val transports: Set<AuthenticatorTransport> = emptySet()
) {
    val clientDataJson =
        """{"challenge":"$challenge","origin":"https://localhost","type":"webauthn.create","tokenBinding":{"status":"supported"}}"""

    val clientDataJsonBytes: ByteArray =
        ByteArray(clientDataJson.toByteArray(Charsets.UTF_8))
    val response: PublicKeyCredential<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs> =
        PublicKeyCredential.builder<AuthenticatorAttestationResponse, ClientRegistrationExtensionOutputs>()
            .id(
                AttestationObject(
                    attestationObject
                ).authenticatorData.attestedCredentialData.get().credentialId
            )
            .response(
                AuthenticatorAttestationResponse
                    .builder()
                    .attestationObject(attestationObject)
                    .clientDataJSON(clientDataJsonBytes)
                    .transports(transports)
                    .build()
            )
            .clientExtensionResults(clientExtensionResults)
            .build()
}