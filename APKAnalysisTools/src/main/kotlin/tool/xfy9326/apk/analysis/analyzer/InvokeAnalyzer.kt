package tool.xfy9326.apk.analysis.analyzer

import tool.xfy9326.apk.analysis.beans.AndroidAPICalls
import tool.xfy9326.apk.analysis.beans.AndroidAPIPermission

class InvokeAnalyzer(
    private val invokeMap: Map<String, AndroidAPIPermission>,
    private val androidApiCall: AndroidAPICalls
) {
    fun getInvokeAPIPermissions(): Set<String> = sequence {
        yieldAll(androidApiCall.fields)
        yieldAll(androidApiCall.methods)
    }.mapNotNull {
        invokeMap[it.toString()]
    }.flatMap {
        it.permissionGroups.asSequence().flatMap { g -> g.permissions }
    }.toSet()
}