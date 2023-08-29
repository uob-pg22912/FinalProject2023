@file:Suppress("unused")

package tool.xfy9326.apk.analysis.android

import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile
import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.Field
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.MultiDexContainer
import com.android.tools.smali.dexlib2.iface.instruction.Instruction
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.*
import tool.xfy9326.apk.analysis.android.visitor.*
import tool.xfy9326.apk.analysis.utils.getDexFiles

class AndroidDexReader(private val dexContainer: MultiDexContainer<out DexBackedDexFile>) {
    private suspend fun DexVisitor.canVisitClass(classDef: ClassDef): Boolean =
        this !is DexClassFilter || onFilterClass(classDef)

    private suspend fun DexVisitor.canVisitMethod(classDef: ClassDef, method: Method, isVirtual: Boolean): Boolean =
        this !is DexMethodFilter || onFilterMethod(classDef, method, isVirtual)

    private suspend fun Iterable<Field?>.traverseFields(visitor: DexFieldVisitor, classDef: ClassDef, isStatic: Boolean) {
        for (field in this) {
            if (field != null) {
                try {
                    visitor.onVisitField(classDef, field, isStatic)
                } catch (_: Exception) {
                }
            }
        }
    }

    private suspend fun Iterable<Method?>.traverseMethods(visitor: DexVisitor, classDef: ClassDef, isVirtual: Boolean) {
        require(visitor is DexMethodVisitor || visitor is DexInstructionVisitor) {
            "Unknown visitor ${visitor::class.simpleName} when traverse method"
        }
        for (method in this) {
            if (method != null) {
                if (visitor is DexMethodVisitor) {
                    try {
                        visitor.onVisitMethod(classDef, method, isVirtual)
                    } catch (_: Exception) {
                    }
                }
                if (visitor is DexInstructionVisitor && visitor.canVisitMethod(classDef, method, isVirtual)) {
                    try {
                        method.implementation?.instructions?.traverseInstructions(visitor, classDef, method, isVirtual)
                    } catch (_: Exception) {
                    }
                }
            }
        }
    }

    private suspend fun Iterable<Instruction?>.traverseInstructions(
        visitor: DexInstructionVisitor,
        classDef: ClassDef,
        method: Method,
        isVirtual: Boolean
    ) {
        for (instruction in this) {
            if (instruction != null) {
                try {
                    visitor.onVisitInstruction(classDef, method, isVirtual, instruction)
                } catch (_: Exception) {
                }
            }
        }
    }

    suspend fun traverseDex(vararg visitors: DexVisitor): Unit = coroutineScope {
        dexContainer.getDexFiles().asFlow().flatMapMerge {
            it.classes.asFlow()
        }.filterNotNull().map {
            async {
                for (visitor in visitors)
                    if (visitor.canVisitClass(it)) {
                        if (visitor is DexClassVisitor) {
                            try {
                                visitor.onVisitClass(it)
                            } catch (_: Exception) {
                            }
                        }
                        if (visitor is DexFieldVisitor) {
                            it.staticFields.traverseFields(visitor, it, true)
                            it.instanceFields.traverseFields(visitor, it, false)
                        }
                        if (visitor is DexMethodVisitor || visitor is DexInstructionVisitor) {
                            it.virtualMethods.traverseMethods(visitor, it, true)
                            it.directMethods.traverseMethods(visitor, it, false)
                        }
                    }
            }
        }.toList().awaitAll()
    }
}