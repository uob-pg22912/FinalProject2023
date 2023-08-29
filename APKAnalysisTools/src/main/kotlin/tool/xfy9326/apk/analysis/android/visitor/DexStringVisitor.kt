package tool.xfy9326.apk.analysis.android.visitor

import com.android.tools.smali.dexlib2.Opcode
import com.android.tools.smali.dexlib2.dexbacked.value.DexBackedStringEncodedValue
import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.Field
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.instruction.Instruction
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction
import com.android.tools.smali.dexlib2.iface.reference.StringReference
import tool.xfy9326.apk.analysis.beans.AnalysisFilter
import tool.xfy9326.apk.analysis.utils.className
import java.util.*

class DexStringVisitor(private val analysisFilter: AnalysisFilter) : DexFieldVisitor, DexInstructionVisitor {
    private val stringPool = Collections.synchronizedSet(HashSet<String>())

    override suspend fun onFilterClass(classDef: ClassDef): Boolean {
        return !analysisFilter.isExcludePackage(classDef.className)
    }

    override suspend fun onVisitField(classDef: ClassDef, field: Field, isStatic: Boolean) {
        val initialValue = field.initialValue
        if (initialValue is DexBackedStringEncodedValue) {
            stringPool.add(initialValue.value)
        }
    }

    override suspend fun onVisitInstruction(classDef: ClassDef, method: Method, isVirtual: Boolean, instruction: Instruction) {
        if (instruction is ReferenceInstruction) {
            if (instruction.opcode == Opcode.CONST_STRING || instruction.opcode == Opcode.CONST_STRING_JUMBO) {
                val ref = instruction.reference
                if (ref is StringReference) {
                    stringPool.add(ref.string)
                }
            }
        }
    }

    fun getOutput(): Set<String> = stringPool
}
