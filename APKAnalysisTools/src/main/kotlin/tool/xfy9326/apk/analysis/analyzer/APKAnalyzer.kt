package tool.xfy9326.apk.analysis.analyzer

import com.android.tools.smali.dexlib2.DexFileFactory
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile
import com.android.tools.smali.dexlib2.iface.MultiDexContainer
import com.reandroid.apk.ApkModule
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import tool.xfy9326.apk.analysis.android.AndroidDexReader
import tool.xfy9326.apk.analysis.android.AndroidInfoManager
import tool.xfy9326.apk.analysis.android.reader.ManifestReader
import tool.xfy9326.apk.analysis.android.reader.ResReader
import tool.xfy9326.apk.analysis.android.visitor.DexAndroidAPICallVisitor
import tool.xfy9326.apk.analysis.android.visitor.DexClassPkgVisitor
import tool.xfy9326.apk.analysis.android.visitor.DexStringVisitor
import tool.xfy9326.apk.analysis.beans.*
import java.io.File


object APKAnalyzer {
    private val APK_MODULE_MUTEX = Mutex()

    private fun File.getDexContainer(): MultiDexContainer<out DexBackedDexFile> =
        DexFileFactory.loadDexContainer(this, null) ?: error("Null dex container")

    private fun File.getApkModule(): ApkModule =
        ApkModule.loadApkFile(this) ?: error("Null apk module")

    private suspend fun File.getResAnalysisResult(): ResAnalysisResult = APK_MODULE_MUTEX.withLock {
        getApkModule().use {
            val manifestReader = ManifestReader(it)
            val resReader = ResReader(it)

            ResAnalysisResult(
                manifestReader.getManifestData(),
                resReader.getStrings(),
                resReader.getStringArrays(),
                resReader.getLayoutTexts()
            )
        }
    }

    private suspend fun File.getDexAnalysisResult(analysisFilter: AnalysisFilter, resResult: ResAnalysisResult): DexAnalysisResult {
        // Prepare mappings
        val authorityClassesMap = AndroidInfoManager.getAuthorityClassesMap()
        val contentProvidersMap = AndroidInfoManager.getContentProvidersMap()
        val trackersIndex = AndroidInfoManager.getTrackersIndex()

        // Prepare mappings by target SDK version
        val dalvikInvokePermission = AndroidInfoManager.getDalvikInvokePermissionMapping(resResult.manifest.targetSDKVersion)

        // Read DEX
        val dexContainer = getDexContainer()

        val reader = AndroidDexReader(dexContainer)

        val pkgVisitor = DexClassPkgVisitor()
        val stringVisitor = DexStringVisitor(analysisFilter)
        val apiVisitor = DexAndroidAPICallVisitor(analysisFilter)

        reader.traverseDex(pkgVisitor, stringVisitor, apiVisitor)

        val pkgNames = pkgVisitor.getOutput()
        val embeddedStrings = stringVisitor.getOutput()
        val androidApiCall = apiVisitor.getOutput()

        // Analyse DEX
        val invokeAPIPermission = InvokeAnalyzer(
            dalvikInvokePermission, androidApiCall
        ).getInvokeAPIPermissions()

        // Analyse strings
        val apkStrings = StringAnalyzer(
            analysisFilter, embeddedStrings, resResult.layoutStrings, resResult.resStrings, resResult.arrayStrings
        ).getAPKStrings()

        // Analyse ContentProviders
        val contentProviderPermissions = ContentProviderAnalyzer(
            apkStrings.uris, androidApiCall, authorityClassesMap, contentProvidersMap
        ).getContentProviderPermissions()

        // Trackers
        val trackerInfoList = TrackersAnalyzer(apkStrings.uris, trackersIndex, pkgNames).getTrackerInfoList()

        return DexAnalysisResult(
            apkStrings,
            DexAPIPermissions(
                resResult.manifest.usePermissions.intersect(invokeAPIPermission).toList().sorted(),
                resResult.manifest.usePermissions.intersect(contentProviderPermissions).toList().sorted()
            ),
            trackerInfoList
        )
    }

    suspend fun getAnalysisResult(
        apkFile: File, analysisFilter: AnalysisFilter
    ): AnalysisResult {
        // Read manifest and resources
        val resResult = apkFile.getResAnalysisResult()

        // Read Dex api permissions
        val dexAnalysisResult = apkFile.getDexAnalysisResult(analysisFilter, resResult)

        // Return result
        return AnalysisResult(
            resResult.manifest,
            dexAnalysisResult.apkStrings,
            dexAnalysisResult.apiPermissions,
            dexAnalysisResult.trackers
        )
    }
}