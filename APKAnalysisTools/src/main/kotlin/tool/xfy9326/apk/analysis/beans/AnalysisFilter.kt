package tool.xfy9326.apk.analysis.beans

import kotlinx.serialization.Serializable

@Serializable
data class AnalysisFilter(
    private val excludePackage: List<String>,
    private val androidAPIPackage: List<String>,
    val excludeString: ExcludeStringConfig,
    private val excludeHosts: Set<String>
) {
    fun isExcludePackage(className: String): Boolean =
        excludePackage.any { className.startsWith("$it.") }

    fun isAndroidAPIPackage(className: String): Boolean =
        androidAPIPackage.any { className.startsWith("$it.") }

    fun isExcludeHost(host: String): Boolean =
        host in excludeHosts

    @Serializable
    data class ExcludeStringConfig(
        private val numberPunctuationRatio: Float,
        private val minStringLength: Int,
        private val prefix: List<String>,
        private val resId: Set<String>
    ) {
        companion object {
            private const val NUM_PUNCTUATION_PATTERN = "\\p{P}|\\d"
        }

        fun isExcludeResId(resId: String): Boolean {
            return resId in this.resId
        }

        fun isExcludeString(text: String): Boolean {
            if (text.length <= minStringLength) {
                return true
            }
            val punctuationSize = NUM_PUNCTUATION_PATTERN.toRegex().findAll(text).count()
            if (punctuationSize.toFloat() / text.length > numberPunctuationRatio) {
                return true
            }
            if (prefix.any { text.startsWith(it) }) {
                return true
            }
            return false
        }
    }
}
