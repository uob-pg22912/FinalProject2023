package tool.xfy9326.apk.analysis.android.reader

import com.reandroid.apk.ApkModule
import com.reandroid.arsc.chunk.xml.AndroidManifestBlock
import com.reandroid.arsc.value.ValueType
import tool.xfy9326.apk.analysis.beans.ManifestData
import tool.xfy9326.apk.analysis.utils.getDefaultResString

class ManifestReader(private val apkModule: ApkModule) {
    @Suppress("ConstPropertyName")
    companion object {
        private const val NAME_minSdkVersion = "minSdkVersion"
        private const val DEFAULT_minSdkVersion = 1
    }

    private fun getPackageName(): String =
        apkModule.packageName ?: error("No package name")

    private fun getMinSDKVersion(): Int =
        apkModule.androidManifestBlock
            ?.manifestElement
            ?.getElementByTagName(AndroidManifestBlock.TAG_uses_sdk)
            ?.searchAttributeByName(NAME_minSdkVersion)
            ?.takeIf {
                it.valueType != ValueType.DEC
            }?.data ?: DEFAULT_minSdkVersion

    private fun getTargetSDKVersion(): Int? =
        apkModule.androidManifestBlock.targetSdkVersion

    private fun getVersionCode(): Int =
        apkModule.androidManifestBlock?.versionCode ?: error("No version code")

    private fun getVersionName(): String =
        apkModule.androidManifestBlock?.versionName ?: ""

    private fun getApplicationName(): String =
        apkModule.androidManifestBlock?.let { block ->
            block.applicationLabelString ?: block.applicationLabelReference?.let {
                apkModule.tableBlock?.getResource(it)?.getDefaultResString()
            }
        } ?: error("No application name")

    private fun getUsePermissions(): List<String> =
        apkModule.androidManifestBlock?.usesPermissions ?: emptyList()

    fun getManifestData(): ManifestData {
        val minSDKVersion = getMinSDKVersion()
        return ManifestData(
            getApplicationName(),
            getPackageName(),
            minSDKVersion,
            getTargetSDKVersion() ?: minSDKVersion,
            getVersionCode(),
            getVersionName(),
            getUsePermissions().sorted(),
        )
    }
}