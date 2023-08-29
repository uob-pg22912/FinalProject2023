@file:Suppress("unused")

package tool.xfy9326.apk.analysis.utils

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlin.coroutines.CoroutineContext


fun <T : Any> suspendCache(
    context: CoroutineContext = Dispatchers.Default,
    initializer: suspend () -> T
) = object : SuspendCache<T>(context, initializer) {}

abstract class SuspendCache<T>(
    private val context: CoroutineContext,
    private val initializer: suspend () -> T
) {
    private var cache: Wrapper<T>? = null
    private val mutex = Mutex()

    suspend fun clear() {
        mutex.withLock {
            cache = null
        }
    }

    fun peek(): T? = cache?.data

    suspend fun value(): T =
        (cache ?: mutex.withLock {
            cache ?: withContext(context) {
                Wrapper(initializer())
            }.also {
                cache = it
            }
        }).data

    private class Wrapper<T>(val data: T)
}
