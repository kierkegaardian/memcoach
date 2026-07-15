package com.memcoach.wrapper

import android.net.Uri

object ServerUrlPolicy {
    fun normalizeBaseUrl(raw: String): String? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) {
            return null
        }
        val withScheme =
            if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
                trimmed
            } else if (isLoopbackInput(trimmed)) {
                "http://$trimmed"
            } else {
                "https://$trimmed"
            }
        val parsed = Uri.parse(withScheme)
        val scheme = parsed.scheme?.lowercase()
        val host = parsed.host?.lowercase()
        return when {
            host.isNullOrBlank() -> null
            scheme == "https" -> withScheme
            scheme == "http" && isLoopbackHost(host) -> withScheme
            else -> null
        }
    }

    fun isAllowedWebHost(target: Uri, currentBaseUrl: String): Boolean {
        val targetScheme = target.scheme?.lowercase() ?: return false
        if (targetScheme != "http" && targetScheme != "https") {
            return false
        }
        val currentUri = Uri.parse(currentBaseUrl)
        val currentScheme = currentUri.scheme?.lowercase() ?: return false
        val currentHost = currentUri.host?.lowercase() ?: return false
        val targetHost = target.host?.lowercase() ?: return false
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

    private fun resolvePort(uri: Uri): Int {
        if (uri.port != -1) {
            return uri.port
        }
        return when (uri.scheme?.lowercase()) {
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
}
