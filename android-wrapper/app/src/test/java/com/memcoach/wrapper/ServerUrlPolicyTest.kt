package com.memcoach.wrapper

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerUrlPolicyTest {
    @Test
    fun normalizesLoopbackAndHttpsBaseUrls() {
        assertEquals("http://127.0.0.1:8000", ServerUrlPolicy.normalizeBaseUrl("127.0.0.1:8000"))
        assertEquals("https://memcoach.example", ServerUrlPolicy.normalizeBaseUrl("memcoach.example"))
    }

    @Test
    fun rejectsAmbiguousOrCredentialedBaseUrls() {
        assertNull(ServerUrlPolicy.normalizeBaseUrl("https://attacker.example\\@memcoach.example"))
        assertNull(ServerUrlPolicy.normalizeBaseUrl("https://user@memcoach.example"))
        assertNull(ServerUrlPolicy.normalizeBaseUrl("http://memcoach.example"))
    }

    @Test
    fun allowsOnlyStrictSameOriginTargets() {
        val baseUrl = "https://memcoach.example"

        assertTrue(ServerUrlPolicy.isAllowedWebHost("https://memcoach.example/review", baseUrl))
        assertTrue(ServerUrlPolicy.isAllowedWebHost("https://memcoach.example:443/review", baseUrl))
        assertFalse(
            ServerUrlPolicy.isAllowedWebHost(
                "https://attacker.example\\@memcoach.example/review",
                baseUrl,
            ),
        )
        assertFalse(ServerUrlPolicy.isAllowedWebHost("https://attacker.example/review", baseUrl))
        assertFalse(ServerUrlPolicy.isAllowedWebHost("https://memcoach.example:8443/review", baseUrl))
    }
}
