@file:Suppress("MemberVisibilityCanBePrivate", "unused")

package tool.xfy9326.apk.analysis.beans

import com.google.common.net.InternetDomainName
import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import tool.xfy9326.apk.analysis.utils.unescapeJava

@Serializable
data class Tracker(
    val id: String,
    val name: String,
    @SerialName("code_signature")
    private val codeSignature: String,
    @SerialName("network_signature")
    private val networkSignature: String,
    @Serializable(with = EmptyStringSerializer::class)
    val website: String?,
    val category: List<String>,
    @SerialName("is_in_exodus")
    val isInExodus: Boolean,
    val documentation: List<String>
) {
    val codeSignatures: List<String> by lazy {
        codeSignature.splitToSequence("|")
            .filterNot {
                it.isBlank()
            }.map {
                it.trim().unescapeJava()
            }.distinct().toList()
    }

    val networkSignatures: List<String> by lazy {
        networkSignature.splitToSequence("|")
            .filterNot {
                it.isBlank()
            }.map {
                it.trim().unescapeJava()
            }.distinct().toList()
    }

    val hasSignatures: Boolean by lazy {
        codeSignatures.isNotEmpty() || networkSignatures.isNotEmpty()
    }

    class EmptyStringSerializer : KSerializer<String?> {
        override val descriptor: SerialDescriptor = PrimitiveSerialDescriptor(javaClass.simpleName, PrimitiveKind.STRING)

        override fun deserialize(decoder: Decoder) =
            decoder.decodeString().takeIf { it.isNotBlank() }

        override fun serialize(encoder: Encoder, value: String?) =
            if (value == null) encoder.encodeNull() else encoder.encodeString(value)
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as Tracker

        return id == other.id
    }

    override fun hashCode(): Int {
        return id.hashCode()
    }
}

@Serializable
data class TrackersWrapper(
    val trackers: List<Tracker>
)

fun Tracker.toTrackerInfo() = TrackerInfo(
    id = id,
    name = name,
    website = website,
    categories = category
)

class TrackersIndex(
    private val trackers: List<Tracker>
) {
    companion object {
        private fun Collection<Tracker>.buildIndex(indexKey: (Tracker) -> Collection<String>) = buildMap<String, MutableList<Tracker>> {
            for (tracker in this@buildIndex) {
                for (signature in indexKey(tracker)) {
                    if (signature in this) {
                        this[signature]?.add(tracker)
                    } else {
                        this[signature] = mutableListOf(tracker)
                    }
                }
            }
        }

        private fun splitDomain(domain: String): List<String> {
            val publicSuffix = InternetDomainName.from(domain).publicSuffix()?.toString()
            val privateIndex = if (publicSuffix == null) {
                domain.length
            } else {
                domain.lastIndexOf(publicSuffix, ignoreCase = true)
            }

            val segments = domain.substring(0, privateIndex).split(".").filter { it.isNotBlank() }.reversed()
            val stringBuilder = StringBuilder(publicSuffix ?: "")
            val results = mutableListOf<String>()

            for (segment in segments) {
                if (stringBuilder.isBlank()) {
                    stringBuilder.append(segment)
                } else {
                    stringBuilder.insert(0, "$segment.")
                }
                results.add(stringBuilder.toString())
            }

            return results.reversed()
        }

        private fun splitPkgName(pkgName: String): List<String> {
            val segments = pkgName.split(".")
            val stringBuilder = StringBuilder()
            val results = mutableListOf<String>()

            for (segment in segments) {
                stringBuilder.append("$segment.")
                results.add(stringBuilder.toString())
            }

            return results.reversed()
        }
    }

    private val networkSignatureIndex = trackers.buildIndex { it.networkSignatures }
    private val codeSignatureIndex = trackers.buildIndex { it.codeSignatures }

    private fun matchAPKUri(apkUri: APKUri): List<Tracker> =
        apkUri.authority.takeIf { InternetDomainName.isValid(it) }?.let {
            splitDomain(it).asSequence().mapNotNull { i ->
                networkSignatureIndex[i]
            }.firstOrNull()
        } ?: emptyList()

    private fun matchPkgName(pkgName: String): List<Tracker> =
        splitPkgName(pkgName).asSequence().mapNotNull {
            codeSignatureIndex[it]
        }.firstOrNull() ?: emptyList()

    fun match(apkUris: Collection<APKUri>, pkgNames: Set<String>): Sequence<Tracker> =
        sequence {
            yieldAll(apkUris.asSequence().flatMap { matchAPKUri(it) })
            yieldAll(pkgNames.asSequence().flatMap { matchPkgName(it) })
        }.distinct()
}
