@file:Suppress("unused")

package tool.xfy9326.apk.analysis.android.visitor

import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.Field
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.instruction.Instruction

sealed interface DexVisitor

interface DexClassVisitor : DexVisitor {
    suspend fun onVisitClass(classDef: ClassDef)
}

interface DexFieldVisitor : DexVisitor, DexClassFilter {
    suspend fun onVisitField(classDef: ClassDef, field: Field, isStatic: Boolean)
}

interface DexMethodVisitor : DexVisitor, DexClassFilter {
    suspend fun onVisitMethod(classDef: ClassDef, method: Method, isVirtual: Boolean)
}

interface DexInstructionVisitor : DexVisitor, DexMethodFilter {
    suspend fun onVisitInstruction(classDef: ClassDef, method: Method, isVirtual: Boolean, instruction: Instruction)
}

sealed interface DexFilter

interface DexClassFilter : DexFilter {
    suspend fun onFilterClass(classDef: ClassDef): Boolean = true
}

interface DexMethodFilter : DexFilter {
    suspend fun onFilterMethod(classDef: ClassDef, method: Method, isVirtual: Boolean): Boolean = true
}
