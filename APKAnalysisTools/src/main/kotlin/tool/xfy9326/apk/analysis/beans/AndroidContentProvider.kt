@file:Suppress("unused")

package tool.xfy9326.apk.analysis.beans

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AndroidAuthorityClass(
    val authority: String,
    @SerialName("names")
    val classNames: List<String>,
    @SerialName("related_names")
    val relatedClassNames: List<String>
)

@Serializable
data class AndroidContentProvider(
    @SerialName("package")
    val packageName: String,
    val name: String,
    val authorities: List<String>,
    val exported: Boolean,
    @SerialName("read_permission")
    val readPermission: String?,
    @SerialName("write_permission")
    val writePermission: String?,
    @SerialName("has_uri_permission")
    val hasUriPermission: Boolean,
    @SerialName("grant_uri_permissions")
    val grantUriPermissions: List<AndroidUriPattern>
) {
    val allPermissions: List<String> by lazy {
        sequenceOf(readPermission, writePermission).filterNotNull().toList()
    }

    fun needReadOrWritePermission(): Boolean =
        readPermission != null && writePermission != null
}

@Serializable
data class AndroidUriPattern(
    val type: String,
    val path: String
)
