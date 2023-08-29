@file:Suppress("unused")

package tool.xfy9326.apk.analysis.beans

import com.android.tools.smali.dexlib2.iface.reference.FieldReference
import com.android.tools.smali.dexlib2.iface.reference.MethodReference
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

private const val API_TYPE_METHOD = "method"
private const val API_TYPE_FIELD = "field"

@Serializable
data class APIPermissionGroup(
    val permissions: List<String>,
    @SerialName("any_of")
    val anyOf: Boolean,
    val conditional: Boolean
)

@Serializable
data class AndroidAPIPermission(
    val api: AndroidAPI,
    @SerialName("permission_groups")
    val permissionGroups: List<APIPermissionGroup>
)

@Serializable
sealed class AndroidAPI {
    abstract val className: String
    abstract val name: String
    abstract val signature: String
    abstract val dalvikDescriptor: String
}

@Serializable
@SerialName(API_TYPE_METHOD)
data class AndroidAPIMethod(
    @SerialName("class_name")
    override val className: String,
    override val name: String,
    override val signature: String,
    @SerialName("dalvik_descriptor")
    override val dalvikDescriptor: String,
    val args: List<String>,
    @SerialName("return_value")
    val returnValue: String,
) : AndroidAPI()

@Serializable
@SerialName(API_TYPE_FIELD)
data class AndroidAPIField(
    @SerialName("class_name")
    override val className: String,
    override val name: String,
    override val signature: String,
    @SerialName("dalvik_descriptor")
    override val dalvikDescriptor: String,
    @SerialName("field_type")
    val type: String,
) : AndroidAPI()

data class AndroidAPICalls(
    val fields: Set<FieldReference>,
    val methods: Set<MethodReference>
)