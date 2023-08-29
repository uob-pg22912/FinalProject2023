package tool.xfy9326.apk.analysis.android.visitor

import com.android.tools.smali.dexlib2.iface.ClassDef
import tool.xfy9326.apk.analysis.utils.packageName

class DexClassPkgVisitor : DexClassVisitor {
    private val pkgNames = mutableSetOf<String>()

    override suspend fun onVisitClass(classDef: ClassDef) {
        classDef.packageName?.let { pkgNames.add(it) }
    }

    fun getOutput(): Set<String> = pkgNames
}