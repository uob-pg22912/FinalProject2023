package tool.xfy9326.apk.analysis.android.visitor

import com.android.tools.smali.dexlib2.Opcode
import com.android.tools.smali.dexlib2.iface.ClassDef
import com.android.tools.smali.dexlib2.iface.Method
import com.android.tools.smali.dexlib2.iface.instruction.Instruction
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction
import com.android.tools.smali.dexlib2.iface.reference.FieldReference
import com.android.tools.smali.dexlib2.iface.reference.MethodReference
import tool.xfy9326.apk.analysis.beans.AnalysisFilter
import tool.xfy9326.apk.analysis.beans.AndroidAPICalls
import tool.xfy9326.apk.analysis.utils.className
import java.util.*

class DexAndroidAPICallVisitor(private val filter: AnalysisFilter) : DexInstructionVisitor {
    companion object {
        private val fieldOpCodes = setOf(
            Opcode.IGET,
            Opcode.IGET_WIDE,
            Opcode.IGET_OBJECT,
            Opcode.IGET_BOOLEAN,
            Opcode.IGET_BYTE,
            Opcode.IGET_CHAR,
            Opcode.IGET_SHORT,
            Opcode.IPUT,
            Opcode.IPUT_WIDE,
            Opcode.IPUT_OBJECT,
            Opcode.IPUT_BOOLEAN,
            Opcode.IPUT_BYTE,
            Opcode.IPUT_CHAR,
            Opcode.IPUT_SHORT,
            Opcode.SGET,
            Opcode.SGET_WIDE,
            Opcode.SGET_OBJECT,
            Opcode.SGET_BOOLEAN,
            Opcode.SGET_BYTE,
            Opcode.SGET_CHAR,
            Opcode.SGET_SHORT,
            Opcode.SPUT,
            Opcode.SPUT_WIDE,
            Opcode.SPUT_OBJECT,
            Opcode.SPUT_BOOLEAN,
            Opcode.SPUT_BYTE,
            Opcode.SPUT_CHAR,
            Opcode.SPUT_SHORT
        )
        private val methodOpCodes = setOf(
            Opcode.INVOKE_VIRTUAL,
            Opcode.INVOKE_SUPER,
            Opcode.INVOKE_DIRECT,
            Opcode.INVOKE_STATIC,
            Opcode.INVOKE_INTERFACE,
            Opcode.INVOKE_VIRTUAL_RANGE,
            Opcode.INVOKE_SUPER_RANGE,
            Opcode.INVOKE_DIRECT_RANGE,
            Opcode.INVOKE_STATIC_RANGE,
            Opcode.INVOKE_INTERFACE_RANGE,
            Opcode.INVOKE_POLYMORPHIC,
            Opcode.INVOKE_POLYMORPHIC_RANGE,
            Opcode.INVOKE_CUSTOM,
            Opcode.INVOKE_CUSTOM_RANGE
        )
    }

    private val fieldPool = Collections.synchronizedSet(HashSet<FieldReference>())
    private val methodPool = Collections.synchronizedSet(HashSet<MethodReference>())

    override suspend fun onFilterMethod(classDef: ClassDef, method: Method, isVirtual: Boolean): Boolean {
        return !filter.isExcludePackage(classDef.className)
    }

    override suspend fun onVisitInstruction(classDef: ClassDef, method: Method, isVirtual: Boolean, instruction: Instruction) {
        if (instruction is ReferenceInstruction) {
            val ref = instruction.reference
            if (instruction.opcode in fieldOpCodes) {
                if (ref is FieldReference && filter.isAndroidAPIPackage(ref.className)) {
                    fieldPool.add(ref)
                }
            } else if (instruction.opcode in methodOpCodes) {
                if (ref is MethodReference && filter.isAndroidAPIPackage(ref.className)) {
                    methodPool.add(ref)
                }
            }
        }
    }

    fun getOutput() =
        AndroidAPICalls(
            fieldPool,
            methodPool
        )
}
