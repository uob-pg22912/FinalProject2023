@file:Suppress("unused")

package tool.xfy9326.apk.analysis.utils

import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile
import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.MultiDexContainer
import com.android.tools.smali.dexlib2.iface.reference.FieldReference
import com.android.tools.smali.dexlib2.iface.reference.MethodReference

private val JVMSignatureMapping = mapOf(
    "I" to "int",
    "J" to "long",
    "F" to "float",
    "D" to "double",
    "B" to "byte",
    "S" to "short",
    "C" to "char",
    "Z" to "boolean",
    "V" to "void",
)

private fun String.signatureToClassName(): String {
    val isArray = startsWith("[")
    val pureSignature = if (isArray) {
        trimStart('[')
    } else {
        this
    }
    val name = JVMSignatureMapping[pureSignature] ?: if (pureSignature.first() == 'L' && pureSignature.last() == ';') {
        pureSignature.substring(1, pureSignature.length - 1).replace("/", ".")
    } else {
        error("Invalid object class name: $this")
    }
    return if (isArray) {
        "$name[]"
    } else {
        name
    }
}

fun MultiDexContainer<out DexBackedDexFile>.getDexFiles(): Sequence<DexBackedDexFile> =
    dexEntryNames.asSequence().mapNotNull { getEntry(it)?.dexFile }

val ClassDef.className: String
    get() = type.signatureToClassName()

val ClassDef.classNameList: List<String>
    get() = className.let {
        if ("." in it) {
            it.split(".")
        } else {
            listOf(it)
        }
    }

val ClassDef.simpleClassName: String
    get() = classNameList.last()

val ClassDef.packageName: String?
    get() = classNameList.takeIf {
        it.size > 1
    }?.dropLast(1)?.joinToString(".")

val MethodReference.className: String
    get() = definingClass.signatureToClassName()

val FieldReference.className: String
    get() = definingClass.signatureToClassName()
