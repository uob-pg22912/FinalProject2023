package tool.xfy9326.apk.analysis.io

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromStream
import tool.xfy9326.apk.analysis.beans.*
import java.io.FileNotFoundException

object LocalResourcesReader {
    private const val ROOT_ASSETS_DIR = "/assets"

    private const val ANALYSIS_FILTER_FILE = "$ROOT_ASSETS_DIR/analysis_filter.json"

    private const val ANDROID_INFO_DIR = "$ROOT_ASSETS_DIR/android_info"
    private const val API_PERMISSION_MAPPINGS_DIR = "$ANDROID_INFO_DIR/api_permission_mappings"
    private const val CONTENT_PROVIDERS_DIR = "$ANDROID_INFO_DIR/content_providers"

    private const val AUTHORITY_CLASSES_FILE = "$CONTENT_PROVIDERS_DIR/authority_classes.json"
    private const val CONTENT_PROVIDER_FILE = "$CONTENT_PROVIDERS_DIR/content_providers.json"

    private val API_PERMISSION_MAPPINGS_VERSIONS = arrayOf(26, 27, 28, 29, 30, 31, 32, 33)
    private val API_PERMISSION_MAPPINGS_FILES: Map<Int, String> =
        API_PERMISSION_MAPPINGS_VERSIONS.associateWith { "$API_PERMISSION_MAPPINGS_DIR/sdk-$it.json" }

    private const val TRACKERS_DIR = "$ANDROID_INFO_DIR/trackers"
    private const val TRACKERS_FILE = "$TRACKERS_DIR/trackers.json"

    fun getAPIPermissionMappingAPIs(): Array<Int> =
        API_PERMISSION_MAPPINGS_VERSIONS.sortedArray()

    private inline fun <reified T> readJSONFromResource(path: String): T =
        javaClass.getResourceAsStream(path)?.use {
            Json.decodeFromStream(it)
        } ?: throw FileNotFoundException(path)

    fun getContentProviderAuthorityClasses(): Map<String, AndroidAuthorityClass> {
        return readJSONFromResource(AUTHORITY_CLASSES_FILE)
    }

    fun getContentProviders(): List<AndroidContentProvider> {
        return readJSONFromResource(CONTENT_PROVIDER_FILE)
    }

    fun getAPIPermissionMappings(apiLevel: Int): List<AndroidAPIPermission> {
        return API_PERMISSION_MAPPINGS_FILES[apiLevel]?.let {
            readJSONFromResource(it)
        } ?: throw IllegalArgumentException("Unsupported API level $apiLevel")
    }

    fun getAnalysisFilter(): AnalysisFilter =
        readJSONFromResource(ANALYSIS_FILTER_FILE)

    fun getTrackers(): List<Tracker> =
        readJSONFromResource<TrackersWrapper>(TRACKERS_FILE).trackers
}