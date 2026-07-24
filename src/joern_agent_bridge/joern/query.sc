import io.shiftleft.semanticcpg.language.*
import io.shiftleft.codepropertygraph.cpgloading.CpgLoader
import io.shiftleft.codepropertygraph.generated.nodes.CfgNode

@main def exec(
  cpgFile: String,
  operation: String,
  method: String,
  pattern: String,
  nodeId: Long,
  direction: String,
  source: String,
  sink: String,
  maxResults: Int,
  maxNodes: Int,
  maxDepth: Int,
  maxPaths: Int
) = {
  val cpg = CpgLoader.load(cpgFile)
  try {

    val result = operation match {
    case "methods" =>
      cpg.method
        .filterNot(_.name.startsWith("<operator>"))
        .take(maxResults)
        .toJson

    case "search_methods" =>
      val selected =
        if (pattern.nonEmpty) cpg.method.name(pattern)
        else cpg.method.nameExact(method)
      selected
        .filterNot(_.name.startsWith("<operator>"))
        .take(maxResults)
        .toJson

    case "cfg" =>
      cpg.method.nameExact(method).cfgNode.take(maxNodes).toJson

    case "neighbors" =>
      val selected = cpg.all.filter(_.id == nodeId).collectAll[CfgNode]
      val outgoing =
        if (direction == "in") Iterator.empty
        else selected.cfgNext
      val incoming =
        if (direction == "out") Iterator.empty
        else cpg.all.filter(_.id == nodeId).collectAll[CfgNode].cfgPrev
      (outgoing ++ incoming).take(maxNodes).toJson

    case "callers" =>
      cpg.method.nameExact(method).caller.take(maxResults).toJson

    case "callees" =>
      cpg.method
        .nameExact(method)
        .callee
        .filterNot(_.name.startsWith("<operator>"))
        .take(maxResults)
        .toJson

    case "control_dependencies" =>
      cpg.method
        .nameExact(method)
        .cfgNode
        .controlledBy
        .dedup
        .take(maxNodes)
        .toJson

    case "dominators" =>
      cpg.method
        .nameExact(method)
        .cfgNode
        .dominatedBy
        .dedup
        .take(maxNodes)
        .toJson

    case "post_dominators" =>
      cpg.method
        .nameExact(method)
        .cfgNode
        .postDominatedBy
        .dedup
        .take(maxNodes)
        .toJson

    case "loops" =>
      cpg.method
        .nameExact(method)
        .ast
        .isControlStructure
        .filter(node => Set("FOR", "WHILE", "DO").contains(node.controlStructureType))
        .take(maxResults)
        .toJson

    case "unreachable" =>
      val starts = cpg.method.nameExact(method).cfgFirst.l
      val reachable =
        starts.map(_.id).toSet ++
          starts.iterator.repeat(_.cfgNext)(_.emit.maxDepth(maxNodes)).id.toSet
      cpg.method
        .nameExact(method)
        .cfgNode
        .filterNot(node => reachable.contains(node.id))
        .take(maxNodes)
        .toJson

    case "call_paths" =>
      cpg.method
        .nameExact(source)
        .enablePathTracking
        .repeat(_.callee)(_.emit.maxDepth(maxDepth))
        .nameExact(sink)
        .path
        .take(maxPaths)
        .toJson

    case "dataflow" =>
      val sources =
        if (source.nonEmpty) cpg.method.name(source).parameter
        else cpg.method.parameter
      val sinks =
        if (sink.nonEmpty) cpg.call.name(sink).argument
        else cpg.call.argument
      sinks
        .reachableByFlows(sources)
        .filter(_.elements.size <= maxDepth)
        .take(maxPaths)
        .toJson

    case "summary" =>
      cpg.method
        .filterNot(_.name.startsWith("<operator>"))
        .take(maxResults)
        .toJson

    case "snapshot" =>
      val selected = cpg.method
        .filterNot(method => method.name.startsWith("<") || method.isExternal)
        .take(maxResults)
        .l
      val methodsJson = selected.iterator.toJson
      val cfgJson = selected.iterator
        .map(method => Map(
          "method" -> method.name,
          "full_name" -> method.fullName,
          "node_count" -> method.start.cfgNode.size
        ))
        .toJson
      val callsJson = selected.iterator
        .flatMap(method =>
          method.start.callee
            .filterNot(_.name.startsWith("<operator>"))
            .map(callee => Map(
              "caller" -> method.name,
              "callee" -> callee.name,
              "callee_full_name" -> callee.fullName
            ))
        )
        .take(maxResults)
        .toJson
      val controlsJson = selected.iterator
        .flatMap(method =>
          method.start.cfgNode.controlledBy.dedup.map(node => Map(
            "method" -> method.name,
            "node_id" -> node.id.toString,
            "code" -> node.code,
            "line" -> node.lineNumber.getOrElse(-1),
            "column" -> node.columnNumber.getOrElse(-1)
          ))
        )
        .take(maxNodes)
        .toJson
      s"""{"methods":$methodsJson,"cfg_summaries":$cfgJson,"calls":$callsJson,"controls":$controlsJson}"""

    case other =>
      throw new IllegalArgumentException(s"unsupported operation: $other")
  }

    println("JOERN_AGENT_RESULT:" + result)
  } finally {
    cpg.close()
  }
}
