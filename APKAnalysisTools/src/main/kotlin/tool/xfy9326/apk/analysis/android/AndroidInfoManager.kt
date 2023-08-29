@file:Suppress("unused")

package tool.xfy9326.apk.analysis.android

import kotlinx.coroutines.Dispatchers
import tool.xfy9326.apk.analysis.beans.AndroidAPIPermission
import tool.xfy9326.apk.analysis.beans.AndroidContentProvider
import tool.xfy9326.apk.analysis.beans.Tracker
import tool.xfy9326.apk.analysis.beans.TrackersIndex
import tool.xfy9326.apk.analysis.io.LocalResourcesReader
import tool.xfy9326.apk.analysis.utils.suspendCache

object AndroidInfoManager {
    private val contentProvidersCacheMap = suspendCache(Dispatchers.IO) {
        buildMap {
            for (provider in LocalResourcesReader.getContentProviders()) {
                for (authority in provider.authorities) {
                    put(authority, provider)
                }
            }
        }
    }
    private val authorityClassCacheMap = suspendCache(Dispatchers.IO) {
        buildMap {
            for (entry in LocalResourcesReader.getContentProviderAuthorityClasses()) {
                for (className in entry.value.classNames) {
                    this[className] = entry.key
                }
                for (className in entry.value.relatedClassNames) {
                    this[className] = entry.key
                }
            }
        }
    }
    private val dalvikDescriptorCacheMap = LocalResourcesReader.getAPIPermissionMappingAPIs().associateWith {
        suspendCache {
            LocalResourcesReader.getAPIPermissionMappings(it).associateBy { p ->
                p.api.dalvikDescriptor
            }
        }
    }
    private val trackersIndexCacheMap = suspendCache(Dispatchers.IO) {
        TrackersIndex(LocalResourcesReader.getTrackers().filter { it.isInExodus && it.hasSignatures })
    }

    suspend fun getContentProvidersMap(): Map<String, AndroidContentProvider> =
        contentProvidersCacheMap.value()

    suspend fun getAuthorityClassesMap(): Map<String, String> =
        authorityClassCacheMap.value()

    private fun getBestMatchAPIVersion(versions: Set<Int>, targetVersion: Int, exactly: Boolean = false): Int? =
        if (targetVersion in versions) {
            targetVersion
        } else if (exactly) {
            null
        } else {
            val sortedVersions = versions.toList().sorted()
            if (sortedVersions.last() < targetVersion) {
                sortedVersions.last()
            } else if (sortedVersions.first() > targetVersion) {
                sortedVersions.first()
            } else {
                sortedVersions.firstOrNull {
                    it > targetVersion
                }
            }
        }

    suspend fun getDalvikInvokePermissionMapping(targetVersion: Int, exactly: Boolean = false): Map<String, AndroidAPIPermission> =
        getBestMatchAPIVersion(dalvikDescriptorCacheMap.keys, targetVersion, exactly)?.let {
            dalvikDescriptorCacheMap[it]?.value()
        } ?: throw NoSuchElementException("No available API version $targetVersion!")

    suspend fun getTrackersIndex(): TrackersIndex = trackersIndexCacheMap.value()
}