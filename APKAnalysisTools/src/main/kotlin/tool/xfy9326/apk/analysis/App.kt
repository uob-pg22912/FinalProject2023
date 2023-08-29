package tool.xfy9326.apk.analysis

import com.github.ajalt.clikt.core.CliktCommand
import com.github.ajalt.clikt.core.context
import com.github.ajalt.clikt.output.MordantHelpFormatter
import com.github.ajalt.clikt.parameters.arguments.argument
import com.github.ajalt.clikt.parameters.arguments.multiple
import com.github.ajalt.clikt.parameters.options.*
import com.github.ajalt.clikt.parameters.types.file
import com.github.ajalt.clikt.parameters.types.int
import com.github.ajalt.clikt.parameters.types.path
import com.github.ajalt.clikt.parameters.types.restrictTo
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromStream
import kotlinx.serialization.json.encodeToStream
import tool.xfy9326.apk.analysis.analyzer.APKAnalyzer
import tool.xfy9326.apk.analysis.beans.AnalysisFilter
import tool.xfy9326.apk.analysis.beans.AnalysisResult
import tool.xfy9326.apk.analysis.io.LocalResourcesReader
import java.io.File
import java.nio.file.Path
import kotlin.coroutines.CoroutineContext
import kotlin.io.path.createDirectories
import kotlin.io.path.notExists
import kotlin.io.path.outputStream

fun main(args: Array<String>) {
    MainCommand().main(args)
}

private class MainCommand : CliktCommand(
    name = "java -jar <File>.jar"
) {
    companion object {
        private const val APK_EXTENSION = "apk"
        private const val APP_NAME = "APKAnalysisTools"

        @OptIn(DelicateCoroutinesApi::class)
        private fun getAnalysisCoroutineContext(workers: Int): CoroutineContext = if (workers > 0) {
            newFixedThreadPoolContext(workers, APP_NAME)
        } else {
            Dispatchers.Default + CoroutineName(APP_NAME)
        }

        private fun AnalysisResult.getOutputName(): String =
            "${manifest.packageName}-${manifest.versionCode}.json"

        private fun List<File>.collectAllAPKs(): Sequence<File> =
            sequence {
                for (file in this@collectAllAPKs) {
                    yieldAll(file.collectAllAPKs())
                }
            }

        private fun File.collectAllAPKs(): Sequence<File> {
            if (isFile) {
                if (extension.equals(APK_EXTENSION, true)) {
                    return sequenceOf(this)
                }
            } else if (isDirectory) {
                listFiles()?.asSequence()?.flatMap {
                    it.collectAllAPKs()
                }?.let {
                    return it
                }
            }
            return emptySequence()
        }
    }

    private val analysisFilter: AnalysisFilter by option(
        help = "Analysis filter config"
    ).file(mustExist = true, canBeDir = false).convert {
        it.inputStream().use { stream ->
            Json.decodeFromStream<AnalysisFilter>(stream)
        }
    }.defaultLazy {
        LocalResourcesReader.getAnalysisFilter()
    }
    private val workers: Int by option(
        help = "Maximum number of APKs analyzed in parallel (0 means default)"
    ).int().restrictTo(min = 0).default(0)
    private val outputDir: Path by option(
        names = arrayOf("-o", "--output"), help = "Output dir"
    ).path(mustExist = false, canBeFile = false).required()
    private val pretty: Boolean by option(
        names = arrayOf("-p", "--pretty"),
        help = "Pretty JSON output"
    ).flag(default = false)
    private val apkFiles: List<File> by argument(
        name = "apks", help = "APK files or dirs"
    ).file(mustExist = true).multiple(required = true)

    private val outputMutex = Mutex()


    init {
        context {
            helpFormatter = { MordantHelpFormatter(it, showDefaultValues = true) }
        }
    }

    override fun run() {
        runBlocking(getAnalysisCoroutineContext(workers)) {
            suspendRun()
        }
    }


    private suspend fun suspendRun() = coroutineScope {
        if (outputDir.notExists()) outputDir.createDirectories()
        val allFiles = apkFiles.collectAllAPKs().toList()

        val json = Json {
            prettyPrint = pretty
            encodeDefaults = true
        }

        var taskCounter = 0
        var failedCounter = 0
        println("Total: ${allFiles.size}")
        allFiles.map { file ->
            async(Dispatchers.Default) {
                try {
                    val analysisResult = APKAnalyzer.getAnalysisResult(file, analysisFilter)
                    val outputPath = outputDir.resolve(analysisResult.getOutputName())
                    withContext(Dispatchers.IO) {
                        outputPath.outputStream().use {
                            json.encodeToStream(analysisResult, it)
                        }
                    }
                    outputMutex.withLock {
                        taskCounter += 1
                        println("Success ($taskCounter/${allFiles.size}): '${file.path}' -> '$outputPath'")
                    }
                } catch (e: Exception) {
                    outputMutex.withLock {
                        taskCounter += 1
                        failedCounter += 1
                        println("Error ($taskCounter/${allFiles.size}): '${file.path}' -> '$e'")
                    }
                }
            }
        }.toList().awaitAll()

        println("Finish: Success -> ${taskCounter - failedCounter} | Failed -> $failedCounter")
    }
}