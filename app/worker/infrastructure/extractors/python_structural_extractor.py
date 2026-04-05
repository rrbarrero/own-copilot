import ast

from app.worker.domain.structural_extractor_proto import (
    StructuralExtractorProto,
    StructuralUnit,
)


class PythonStructuralExtractor(StructuralExtractorProto):
    def extract(self, text: str, language: str) -> list[StructuralUnit]:
        if language.lower() not in ["py", "python"]:
            return []

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []

        units = []
        # Extract individual classes and functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                # Get the source code of the node content if possible
                # However, for simplicity and stability across Python versions,
                # we'll just track the lines for now.
                content = ast.get_source_segment(text, node)
                if content:
                    u_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    units.append(
                        StructuralUnit(
                            name=node.name,
                            unit_type=u_type,
                            content=content,
                            start_chunk_idx=0,  # Need to map these later
                            end_chunk_idx=0,
                        )
                    )

        # Add module-level summary unit (the whole file)
        units.append(
            StructuralUnit(
                name="module",
                unit_type="module",
                content=text,
                start_chunk_idx=0,
                end_chunk_idx=0,
            )
        )

        return units
