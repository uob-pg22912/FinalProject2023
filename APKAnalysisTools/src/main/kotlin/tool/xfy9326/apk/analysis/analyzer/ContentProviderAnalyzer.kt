package tool.xfy9326.apk.analysis.analyzer

import tool.xfy9326.apk.analysis.beans.APKUri
import tool.xfy9326.apk.analysis.beans.AndroidAPICalls
import tool.xfy9326.apk.analysis.beans.AndroidContentProvider
import tool.xfy9326.apk.analysis.utils.className

class ContentProviderAnalyzer(
    private val apkUris: Collection<APKUri>,
    private val androidApiCall: AndroidAPICalls,
    private val authorityClassesMap: Map<String, String>,
    private val contentProvidersMap: Map<String, AndroidContentProvider>
) {
    companion object {
        private const val PROTOCOL_CONTENT = "content"
        private const val ANDROID_PROVIDER_PACKAGE = "android.provider."
    }

    private fun getInvokeContentProviders(): Sequence<AndroidContentProvider> = sequence {
        yieldAll(androidApiCall.fields.asSequence().filter {
            it.className.startsWith(ANDROID_PROVIDER_PACKAGE)
        }.map {
            it.className
        })
        yieldAll(androidApiCall.methods.asSequence().filter {
            it.className.startsWith(ANDROID_PROVIDER_PACKAGE)
        }.map {
            it.className
        })
    }.mapNotNull {
        authorityClassesMap[it]
    }.mapNotNull {
        contentProvidersMap[it]
    }.distinct()

    private fun getUriContentProviders(): Sequence<AndroidContentProvider> =
        apkUris.asSequence().filter {
            it.protocol.equals(PROTOCOL_CONTENT, ignoreCase = true)
        }.mapNotNull {
            contentProvidersMap[it.authority]
        }.distinct()

    fun getContentProviderPermissions(): Set<String> = sequence {
        yieldAll(getInvokeContentProviders())
        yieldAll(getUriContentProviders())
    }.flatMap {
        it.allPermissions.asSequence()
    }.toSet()
}