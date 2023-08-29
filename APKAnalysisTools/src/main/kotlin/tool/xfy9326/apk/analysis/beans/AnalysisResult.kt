package tool.xfy9326.apk.analysis.beans

import kotlinx.serialization.KSerializer
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import java.net.URI

@Serializable
data class AnalysisResult(
    val manifest: ManifestData,
    val strings: APKStrings,
    val dexAPIPermissions: DexAPIPermissions,
    val trackers: List<TrackerInfo>
)

@Serializable
data class TrackerInfo(
    val id: String,
    val name: String,
    val website: String?,
    val categories: List<String>
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as TrackerInfo

        return id == other.id
    }

    override fun hashCode(): Int {
        return id.hashCode()
    }
}

@Serializable
data class ManifestData(
    val applicationName: String,
    val packageName: String,
    val minSDKVersion: Int,
    val targetSDKVersion: Int,
    val versionCode: Int,
    val versionName: String,
    val usePermissions: List<String>,
)

@Serializable
data class APKStrings(
    val ipv4: List<String>,
    val uris: List<APKUri>,
    val embeddedStrings: List<String>,
    val layoutStrings: List<String>,
    val resStrings: Map<String, String>,
    val arrayStrings: Map<String, List<String>>
)

@Serializable(APKUri.Serializer::class)
data class APKUri(
    val uri: String,
    val authority: String,
    val protocol: String
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as APKUri

        return uri == other.uri
    }

    override fun hashCode(): Int {
        return uri.hashCode()
    }

    class Serializer : KSerializer<APKUri> {
        override val descriptor: SerialDescriptor = PrimitiveSerialDescriptor(javaClass.simpleName, PrimitiveKind.STRING)

        override fun deserialize(decoder: Decoder) = URI(decoder.decodeString()).let {
            APKUri(it.toString(), it.authority, it.scheme)
        }

        override fun serialize(encoder: Encoder, value: APKUri) = encoder.encodeString(value.uri)
    }
}

@Serializable
data class DexAPIPermissions(
    val apiCallPermissions: List<String>,
    val contentProviderPermissions: List<String>,
)

data class ResAnalysisResult(
    val manifest: ManifestData,
    val resStrings: Map<String, String>,
    val arrayStrings: Map<String, List<String>>,
    val layoutStrings: List<String>
)

data class DexAnalysisResult(
    val apkStrings: APKStrings,
    val apiPermissions: DexAPIPermissions,
    val trackers: List<TrackerInfo>
)

