package com.memcoach.wrapper

import java.net.URI
import java.net.URISyntaxException

object ServerUrlPolicy {
    fun normalizeBaseUrl(raw: String): String? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) {
            return null
        }
        val withScheme =
            if (
                trimmed.startsWith("http://", ignoreCase = true) ||
                trimmed.startsWith("https://", ignoreCase = true)
            ) {
                trimmed
            } else if (isLoopbackInput(trimmed)) {
                "http://$trimmed"
            } else {
                "https://$trimmed"
            }
        val parsed = parseStrictWebUri(withScheme) ?: return null
        val scheme = parsed.scheme.lowercase()
        val host = parsed.host.lowercase()
        return when {
            scheme == "https" -> withScheme
            scheme == "http" && isLoopbackHost(host) -> withScheme
            else -> null
        }
    }

    fun isAllowedWebHost(targetUrl: String, currentBaseUrl: String): Boolean {
        val target = parseStrictWebUri(targetUrl) ?: return false
        val currentUri = parseStrictWebUri(currentBaseUrl) ?: return false
        val targetScheme = target.scheme.lowercase()
        val currentScheme = currentUri.scheme.lowercase()
        val currentHost = currentUri.host.lowercase()
        val targetHost = target.host.lowercase()
        if (currentScheme != targetScheme || currentHost != targetHost) {
            return false
        }
        if (targetScheme == "http" && !isLoopbackHost(targetHost)) {
            return false
        }
        return resolvePort(target) == resolvePort(currentUri)
    }

    fun isGatewayOrEdgeError(statusCode: Int): Boolean {
        return statusCode in setOf(502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530)
    }

    private fun resolvePort(uri: URI): Int {
        if (uri.port != -1) {
            return uri.port
        }
        return when (uri.scheme.lowercase()) {
            "https" -> 443
            "http" -> 80
            else -> -1
        }
    }

    private fun isLoopbackInput(raw: String): Boolean {
        val withoutScheme = raw.removePrefix("http://").removePrefix("https://")
        val hostPart = withoutScheme.substringBefore("/").substringBefore(":").lowercase()
        return isLoopbackHost(hostPart)
    }

    private fun isLoopbackHost(host: String): Boolean {
        return host == "localhost" || host == "127.0.0.1"
    }

    private fun parseStrictWebUri(raw: String): URI? {
        if ('\\' in raw) {
            return null
        }
        val parsed =
            try {
                URI(raw)
            } catch (_: URISyntaxException) {
                return null
            }
        val scheme = parsed.scheme?.lowercase() ?: return null
        if (scheme != "http" && scheme != "https") {
            return null
        }
        if (parsed.host.isNullOrBlank() || parsed.rawUserInfo != null) {
            return null
        }
        return parsed
    }
}
