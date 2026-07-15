package com.memcoach.wrapper

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.webkit.PermissionRequest
import android.webkit.WebResourceError
import android.webkit.WebResourceResponse
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    private val defaultStartUrl = BuildConfig.MEMCOACH_START_URL
    private val prefsName = "memcoach_wrapper"
    private val baseUrlPrefKey = "base_url"

    private lateinit var webView: WebView
    private var currentBaseUrl: String = defaultStartUrl
    private var showingBaseUrlPrompt = false
    private var allowUrlPromptLongPress = false
    private var pendingPermissionRequest: PermissionRequest? = null

    private val micPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val request = pendingPermissionRequest
        pendingPermissionRequest = null
        if (granted && request != null && isTrustedAudioPermissionRequest(request)) {
            request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
        } else {
            request?.deny()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            allowContentAccess = false
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val target = request?.url ?: return false
                val scheme = target.scheme?.lowercase() ?: return true
                if (scheme != "http" && scheme != "https") {
                    return openExternalUrl(target)
                }
                if (ServerUrlPolicy.isAllowedWebHost(target.toString(), currentBaseUrl)) {
                    return false
                }
                return openExternalUrl(target)
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame != true) {
                    return
                }
                if (error == null) {
                    return
                }
                if (
                    error.errorCode == WebViewClient.ERROR_HOST_LOOKUP ||
                    error.errorCode == WebViewClient.ERROR_BAD_URL ||
                    error.errorCode == WebViewClient.ERROR_CONNECT ||
                    error.errorCode == WebViewClient.ERROR_TIMEOUT ||
                    error.errorCode == WebViewClient.ERROR_FAILED_SSL_HANDSHAKE
                ) {
                    allowUrlPromptLongPress = true
                    promptForBaseUrl()
                }
            }

            override fun onReceivedHttpError(
                view: WebView?,
                request: WebResourceRequest?,
                errorResponse: WebResourceResponse?
            ) {
                if (request?.isForMainFrame != true) {
                    return
                }
                val statusCode = errorResponse?.statusCode ?: return
                if (ServerUrlPolicy.isGatewayOrEdgeError(statusCode)) {
                    allowUrlPromptLongPress = true
                    promptForBaseUrl()
                }
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                val loaded = url ?: return
                if (ServerUrlPolicy.isAllowedWebHost(loaded, currentBaseUrl)) {
                    allowUrlPromptLongPress = false
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    val resources = request.resources
                    if (!isTrustedAudioPermissionRequest(request)) {
                        request.deny()
                    } else if (resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) {
                        if (hasMicPermission()) {
                            request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                        } else {
                            pendingPermissionRequest = request
                            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    } else {
                        request.deny()
                    }
                }
            }

            override fun onPermissionRequestCanceled(request: PermissionRequest) {
                if (pendingPermissionRequest == request) {
                    pendingPermissionRequest = null
                }
            }

            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                filePathCallback?.onReceiveValue(null)
                return false
            }
        }

        currentBaseUrl = loadBaseUrl()
        webView.setOnLongClickListener {
            if (!allowUrlPromptLongPress) {
                return@setOnLongClickListener false
            }
            promptForBaseUrl()
            true
        }

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            webView.loadUrl(currentBaseUrl)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onDestroy() {
        pendingPermissionRequest?.deny()
        pendingPermissionRequest = null
        webView.destroy()
        super.onDestroy()
    }

    private fun isTrustedAudioPermissionRequest(request: PermissionRequest): Boolean {
        return request.resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE) &&
            ServerUrlPolicy.isAllowedWebHost(request.origin.toString(), currentBaseUrl)
    }

    private fun hasMicPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun loadBaseUrl(): String {
        val stored = getSharedPreferences(prefsName, MODE_PRIVATE)
            .getString(baseUrlPrefKey, defaultStartUrl)
            ?.trim()
            .orEmpty()
        return ServerUrlPolicy.normalizeBaseUrl(stored)
            ?: ServerUrlPolicy.normalizeBaseUrl(defaultStartUrl)
            ?: "http://127.0.0.1:8000"
    }

    private fun saveBaseUrl(url: String) {
        getSharedPreferences(prefsName, MODE_PRIVATE)
            .edit()
            .putString(baseUrlPrefKey, url)
            .apply()
    }

    private fun promptForBaseUrl() {
        if (showingBaseUrlPrompt) {
            return
        }
        showingBaseUrlPrompt = true

        val input = EditText(this).apply {
            hint = "http://127.0.0.1:8000 or https://your-server-url"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setText(currentBaseUrl)
            setSelection(text.length)
        }

        val dialog = AlertDialog.Builder(this)
            .setTitle("MemCoach server not reachable")
            .setMessage("If the server address changed, update it and tap Reload.")
            .setView(input)
            .setCancelable(true)
            .setPositiveButton("Reload", null)
            .setNegativeButton("Cancel", null)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val normalized = ServerUrlPolicy.normalizeBaseUrl(input.text.toString())
                if (normalized != null) {
                    currentBaseUrl = normalized
                    saveBaseUrl(normalized)
                    webView.loadUrl(normalized)
                    dialog.dismiss()
                } else {
                    Toast.makeText(
                        this,
                        "Enter http://127.0.0.1:8000 or a valid HTTPS URL",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
        dialog.setOnDismissListener {
            showingBaseUrlPrompt = false
        }
        dialog.show()
    }

    private fun openExternalUrl(target: Uri): Boolean {
        return try {
            startActivity(Intent(Intent.ACTION_VIEW, target))
            true
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No app found to open this link.", Toast.LENGTH_SHORT).show()
            true
        }
    }

}
