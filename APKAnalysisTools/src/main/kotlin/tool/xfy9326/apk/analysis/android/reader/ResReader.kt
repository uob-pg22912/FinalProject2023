package tool.xfy9326.apk.analysis.android.reader

import com.reandroid.apk.ApkModule
import com.reandroid.xml.XMLElement
import tool.xfy9326.apk.analysis.utils.flattenAllElements
import tool.xfy9326.apk.analysis.utils.getDefaultResStringArrayMap
import tool.xfy9326.apk.analysis.utils.getDefaultResStrings
import tool.xfy9326.apk.analysis.utils.getDefaultResStringsMap

class ResReader(private val apkModule: ApkModule) {
    companion object {
        private const val NAMESPACE_ANDROID = "android"
        private const val NAMESPACE_APP = "app"

        private const val ATTR_TEXT = "text"
        private const val ATTR_HINT = "hint"
        private const val ATTR_TITLE = "title"
        private const val ATTR_CONTENT_DESCRIPTION = "contentDescription"

        private const val RES_TYPE_STRING = "string"
        private const val RES_TYPE_ARRAY = "array"
        private const val RES_TYPE_LAYOUT = "layout"
        private const val RES_TYPE_MENU = "menu"

        private const val RES_PREFIX = "@"
        private const val REF_PREFIX = "?"

        @Suppress("HttpUrlsUsage")
        private val ANDROID_MANIFEST_NAMESPACES = mapOf(
            "android" to "http://schemas.android.com/apk/res/android",
            "tools" to "http://schemas.android.com/tools",
            "app" to "http://schemas.android.com/apk/res-auto",
        )

        private val xmlTextAttributes: List<String> by lazy {
            val namespaceArray = arrayOf(NAMESPACE_ANDROID, NAMESPACE_APP)
            val attrNameArray = arrayOf(ATTR_TEXT, ATTR_HINT, ATTR_TITLE, ATTR_CONTENT_DESCRIPTION)
            buildList {
                namespaceArray.forEach { ns ->
                    attrNameArray.forEach { name ->
                        add("$ns:$name")
                    }
                }
            }
        }
    }

    private fun XMLElement.getResXmlText(): Sequence<String> =
        flattenAllElements().flatMap { element ->
            xmlTextAttributes.asSequence().map {
                element.getAttribute(it)
            }
        }.mapNotNull {
            it?.value
        }.filterNot {
            it.startsWith(RES_PREFIX) || it.startsWith(REF_PREFIX)
        }

    fun getStrings(): Map<String, String> =
        apkModule.tableBlock?.getDefaultResStringsMap(RES_TYPE_STRING) ?: emptyMap()

    fun getStringArrays(): Map<String, List<String>> =
        apkModule.tableBlock?.getDefaultResStringArrayMap(RES_TYPE_ARRAY) ?: emptyMap()

    fun getLayoutTexts(): List<String> {
        val tableBlock = apkModule.tableBlock ?: error("No resources content")
        return sequence {
            yieldAll(tableBlock.getDefaultResStrings(RES_TYPE_LAYOUT))
            yieldAll(tableBlock.getDefaultResStrings(RES_TYPE_MENU))
        }.flatMap {
            try {
                apkModule.loadResXmlDocument(it).resXmlElement.also { res ->
                    for ((prefix, uri) in ANDROID_MANIFEST_NAMESPACES) {
                        if (res.getNamespaceByPrefix(prefix) == null) {
                            res.newNamespace(uri, prefix)
                        }
                    }
                }.decodeToXml().getResXmlText()
            } catch (e: Exception) {
                emptySequence()
            }
        }.toList()
    }
}