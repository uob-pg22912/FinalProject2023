package tool.xfy9326.apk.analysis

import kotlinx.coroutines.runBlocking
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import tool.xfy9326.apk.analysis.analyzer.APKAnalyzer
import tool.xfy9326.apk.analysis.io.LocalResourcesReader
import java.io.File
import kotlin.test.Test

class TestMain {
    @Test
    fun runMain() = runBlocking {
        val file = File("test.apk")
        val filter = LocalResourcesReader.getAnalysisFilter()
        val analysisResult = APKAnalyzer.getAnalysisResult(file, filter)
        val json = Json {
            prettyPrint = true
            encodeDefaults = true
        }
        println(json.encodeToString(analysisResult))
    }
}