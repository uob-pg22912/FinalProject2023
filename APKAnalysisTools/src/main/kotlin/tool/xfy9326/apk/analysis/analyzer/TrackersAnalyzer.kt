package tool.xfy9326.apk.analysis.analyzer

import tool.xfy9326.apk.analysis.beans.APKUri
import tool.xfy9326.apk.analysis.beans.TrackerInfo
import tool.xfy9326.apk.analysis.beans.TrackersIndex
import tool.xfy9326.apk.analysis.beans.toTrackerInfo

class TrackersAnalyzer(
    private val apkUris: Collection<APKUri>,
    private val trackersIndex: TrackersIndex,
    private val pkgNames: Set<String>
) {
    fun getTrackerInfoList(): List<TrackerInfo> =
        trackersIndex.match(apkUris, pkgNames).map {
            it.toTrackerInfo()
        }.toList()
}