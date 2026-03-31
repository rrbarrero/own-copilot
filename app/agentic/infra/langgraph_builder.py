import logging

from langgraph.graph import END, START, StateGraph

from app.agentic.application.nodes.answer_from_context import AnswerFromContextNode
from app.agentic.application.nodes.decide_next_action import DecideNextActionNode
from app.agentic.application.nodes.evaluate_evidence import EvaluateEvidenceNode
from app.agentic.application.nodes.rewrite_question import RewriteQuestionNode
from app.agentic.application.nodes.run_find_files import RunFindFilesNode
from app.agentic.application.nodes.run_rag import RunRagNode
from app.agentic.application.nodes.run_read_file import RunReadFileNode
from app.agentic.application.nodes.run_search_in_repo import RunSearchInRepoNode
from app.agentic.application.nodes.stop_no_evidence import StopNoEvidenceNode
from app.agentic.domain.graph_state import AgentGraphState

logger = logging.getLogger(__name__)


class LangGraphBuilder:
    def __init__(
        self,
        rewrite_node: RewriteQuestionNode,
        decide_node: DecideNextActionNode,
        rag_node: RunRagNode,
        find_files_node: RunFindFilesNode,
        read_file_node: RunReadFileNode,
        search_in_repo_node: RunSearchInRepoNode,
        evaluate_node: EvaluateEvidenceNode,
        answer_node: AnswerFromContextNode,
        stop_no_evidence_node: StopNoEvidenceNode,
    ):
        self._rewrite = rewrite_node
        self._decide = decide_node
        self._rag = rag_node
        self._find_files = find_files_node
        self._read_file = read_file_node
        self._search_in_repo = search_in_repo_node
        self._evaluate = evaluate_node
        self._answer = answer_node
        self._stop_no_evidence = stop_no_evidence_node

    def build(self):
        """
        Assembles the LangGraph.
        """
        workflow = StateGraph(AgentGraphState)  # type: ignore

        # Add nodes
        workflow.add_node("rewrite", self._rewrite)  # type: ignore
        workflow.add_node("decide", self._decide)  # type: ignore
        workflow.add_node("rag", self._rag)  # type: ignore
        workflow.add_node("find_files", self._find_files)  # type: ignore
        workflow.add_node("read_file", self._read_file)  # type: ignore
        workflow.add_node("search_in_repo", self._search_in_repo)  # type: ignore
        workflow.add_node("evaluate", self._evaluate)  # type: ignore
        workflow.add_node("answer", self._answer)  # type: ignore
        workflow.add_node("stop_no_evidence", self._stop_no_evidence)  # type: ignore

        # Define edges
        workflow.add_edge(START, "rewrite")
        workflow.add_edge("rewrite", "decide")

        # Routing from Decide
        def route_after_decide(state: AgentGraphState):
            strategy = state["current_strategy"]
            logger.info(
                "graph_route.after_decide conversation_id=%s strategy=%s step_count=%s",
                state["conversation_id"],
                strategy,
                state["step_count"],
            )
            if strategy in [
                "find_files",
                "read_file",
                "search_in_repo",
                "rag",
                "stop_no_evidence",
            ]:
                return strategy
            return "answer"

        workflow.add_conditional_edges(
            "decide",
            route_after_decide,
            {
                "rag": "rag",
                "find_files": "find_files",
                "read_file": "read_file",
                "search_in_repo": "search_in_repo",
                "answer": "answer",
                "stop_no_evidence": "stop_no_evidence",
            },
        )

        # All actions go to evaluate
        workflow.add_edge("rag", "evaluate")
        workflow.add_edge("find_files", "evaluate")
        workflow.add_edge("read_file", "evaluate")
        workflow.add_edge("search_in_repo", "evaluate")

        # Evaluate goes back to decide or completes with answer
        def route_after_evaluate(state: AgentGraphState):
            destination = "answer" if state.get("done", False) else "decide"
            logger.info(
                "graph_route.after_evaluate conversation_id=%s done=%s "
                "next=%s step_count=%s",
                state["conversation_id"],
                state.get("done", False),
                destination,
                state["step_count"],
            )
            if state.get("done", False):
                return "answer"
            return "decide"

        workflow.add_conditional_edges(
            "evaluate", route_after_evaluate, {"decide": "decide", "answer": "answer"}
        )

        # Final answer goes to end
        workflow.add_edge("answer", END)
        workflow.add_edge("stop_no_evidence", END)

        return workflow.compile()
