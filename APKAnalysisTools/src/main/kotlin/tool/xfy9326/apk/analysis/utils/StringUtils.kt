package tool.xfy9326.apk.analysis.utils

import org.apache.commons.text.StringEscapeUtils


fun String.unescapeJava(): String =
    StringEscapeUtils.unescapeJava(this)
