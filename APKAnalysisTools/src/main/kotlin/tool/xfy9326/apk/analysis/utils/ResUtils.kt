@file:Suppress("unused")

package tool.xfy9326.apk.analysis.utils

import com.reandroid.arsc.chunk.TableBlock
import com.reandroid.arsc.model.ResourceEntry
import com.reandroid.arsc.value.Entry
import com.reandroid.arsc.value.ValueType
import com.reandroid.xml.XMLElement

fun XMLElement.flattenAllElements(): Sequence<XMLElement> = sequence {
    yield(this@flattenAllElements)
    yieldAll(childElementList.asSequence().flatMap { e -> e.flattenAllElements() })
}

fun TableBlock.getEntries(type: String): Sequence<Entry> = listPackages().asSequence().mapNotNull {
    it?.getSpecTypePair(type)
}.flatMap {
    it.listTypeBlocks()
}.filterNotNull().flatMap {
    it.listEntries(true)
}

fun TableBlock.getResourceEntries(type: String): Sequence<ResourceEntry> = listPackages().asSequence().filterNotNull().flatMap {
    it.resources.asSequence()
}.filterNotNull().filter {
    it.type == type
}

private fun Entry.isRegion(code: String): Boolean = resConfig?.region?.equals(code, true) ?: false

private fun Entry.isLanguage(code: String): Boolean = resConfig?.language?.equals(code, true) ?: false


fun ResourceEntry.getDefaultRes(): Entry? =
    asSequence().filterNotNull().filterNot { it.isNull }.sortedByDescending {
        when {
            it.isLanguage("en") -> 10
            it.isRegion("US") -> 8
            it.isRegion("GB") -> 7
            it.isDefault -> 5
            else -> 0
        }
    }.firstOrNull()

fun ResourceEntry.getDefaultResString(): String? =
    getDefaultRes()?.resValue?.let {
        if (it.valueType != ValueType.REFERENCE) {
            it.valueAsString
        } else {
            it.resolve(it.data)?.resolveReference()?.get()?.resValue?.valueAsString
        }
    }

fun ResourceEntry.getDefaultResStringArray(): List<String>? =
    getDefaultRes()?.resTableMapEntry?.takeIf { it.isArray }?.mapNotNull {
        if (it.valueType == ValueType.STRING) {
            it.valueAsString
        } else {
            null
        }
    }

fun TableBlock.getDefaultResStrings(type: String): List<String> = getResourceEntries(type).mapNotNull {
    it.getDefaultResString()
}.filter { it.isNotBlank() }.toList()

fun TableBlock.getDefaultResStringsMap(type: String): Map<String, String> = getResourceEntries(type).mapNotNull {
    val name = it.name
    val text = it.getDefaultResString()
    if (name != null && !text.isNullOrBlank()) {
        name to text
    } else {
        null
    }
}.toMap()

fun TableBlock.getDefaultResStringArrayMap(type: String): Map<String, List<String>> = getResourceEntries(type).mapNotNull {
    val name = it.name
    val textArray = it.getDefaultResStringArray()
    if (name != null && !textArray.isNullOrEmpty()) {
        name to textArray
    } else {
        null
    }
}.toMap()
