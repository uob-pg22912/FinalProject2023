package tool.xfy9326.apk.analysis.analyzer

import tool.xfy9326.apk.analysis.beans.APKStrings
import tool.xfy9326.apk.analysis.beans.APKUri
import tool.xfy9326.apk.analysis.beans.AnalysisFilter
import java.net.URI

class StringAnalyzer(
    private val filter: AnalysisFilter,
    private val embeddedString: Collection<String>,
    private val xmlString: Collection<String>,
    private val resString: Map<String, String>,
    private val arrayString: Map<String, List<String>>,
) {
    private val uriRegex = "[a-zA-Z]+://[-a-zA-Z0-9+&@#/%?=~_|!:,.;]*[-a-zA-Z0-9+&@#/%=~_|]".toRegex(RegexOption.IGNORE_CASE)
    private val ipv4Regex = "^((25[0-5]|(2[0-4]|1\\d|[1-9]|)\\d)\\.?\\b){4}\$".toRegex()
    private val lineBreakAndSpaceRegex = "\\R+|\\s+".toRegex()

    private fun String.cleanText(): String =
        replace(lineBreakAndSpaceRegex, " ").trim()

    private fun String.getUris(): Sequence<APKUri> =
        uriRegex.findAll(this).mapNotNull {
            try {
                val text = it.value.trim()
                val uri = URI(text)
                if (uri.authority != null && uri.scheme != null) {
                    APKUri(text, uri.authority, uri.scheme)
                } else {
                    null
                }
            } catch (e: Exception) {
                null
            }
        }

    private fun String.getIPV4(): Sequence<String> =
        ipv4Regex.findAll(this).map { it.value.trim() }

    private fun Collection<String>.preprocess(
        ipv4: MutableSet<String>,
        uris: MutableSet<APKUri>
    ): Sequence<String> =
        asSequence().map {
            it.cleanText()
        }.filterNot {
            it.isBlank()
        }.onEach {
            ipv4.addAll(it.getIPV4())
            uris.addAll(it.getUris())
        }.filterNot {
            filter.excludeString.isExcludeString(it)
        }.distinct()

    private fun Map<String, String>.preprocessResString(
        ipv4: MutableSet<String>,
        uris: MutableSet<APKUri>
    ): Sequence<Pair<String, String>> =
        asSequence().map {
            it.key to it.value.cleanText()
        }.filterNot {
            it.second.isBlank()
        }.onEach {
            ipv4.addAll(it.second.getIPV4())
            uris.addAll(it.second.getUris())
        }.filterNot {
            filter.excludeString.isExcludeResId(it.first)
        }.filterNot {
            filter.excludeString.isExcludeString(it.second)
        }.distinct()


    private fun Map<String, List<String>>.preprocessResArray(
        ipv4: MutableSet<String>,
        uris: MutableSet<APKUri>
    ): Sequence<Pair<String, List<String>>> =
        asSequence().map {
            it.key to it.value.map { i -> i.cleanText() }.filterNot { i -> i.isBlank() }
        }.filterNot {
            it.second.isEmpty()
        }.onEach {
            ipv4.addAll(it.second.asSequence().flatMap { i -> i.getIPV4() })
            uris.addAll(it.second.asSequence().flatMap { i -> i.getUris() })
        }.filterNot {
            filter.excludeString.isExcludeResId(it.first)
        }.map {
            it.first to it.second.filterNot { i -> filter.excludeString.isExcludeString(i) }
        }.filterNot {
            it.second.isEmpty()
        }.distinct()

    fun getAPKStrings(): APKStrings {
        val ipv4 = mutableSetOf<String>()
        val uris = mutableSetOf<APKUri>()

        val embedded = embeddedString.preprocess(ipv4, uris).toList()
        val layout = xmlString.preprocess(ipv4, uris).toList()
        val res = resString.preprocessResString(ipv4, uris).toMap()
        val array = arrayString.preprocessResArray(ipv4, uris).toMap()

        return APKStrings(
            ipv4 = ipv4.toList(),
            uris = uris.filterNot { filter.isExcludeHost(it.authority) }.toList(),
            embeddedStrings = embedded,
            layoutStrings = layout,
            resStrings = res,
            arrayStrings = array
        )
    }
}