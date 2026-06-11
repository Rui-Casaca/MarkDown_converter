"""European Portuguese UI string catalog for doc2md."""

from __future__ import annotations

CATALOG: dict[str, str] = {
    # Header
    "app.subtitle": (
        "Converte documentos PDF, Word DOCX e PowerPoint PPTX em Markdown limpo, "
        "otimizado para leitura por IA, sumarização, embeddings, ingestão RAG e resposta a perguntas."
    ),
    "label.language": "Idioma:",
    # Frame titles
    "frame.input": "Configuração de entrada",
    "frame.output": "Configuração de saída",
    "frame.format": "Seleção de formatos",
    "frame.options": "Opções de conversão",
    "frame.progress": "Progresso",
    "frame.log": "Registo",
    # Labels
    "label.input_mode": "Modo de entrada:",
    "label.selected_input": "Entrada selecionada:",
    "label.output_markdown": "Markdown de saída:",
    "label.header_style": "Estilo do cabeçalho:",
    "input.files_selected": "{n} ficheiros selecionados",
    # Input mode combobox values
    "mode.single": "Ficheiro único",
    "mode.multiple": "Vários ficheiros",
    "mode.folder": "Pasta",
    # Header style combobox values
    "headerstyle.blockquote": "Citação",
    "headerstyle.yaml": "Front matter YAML",
    # Conversion option checkboxes
    "check.metadata": "Incluir metadados do documento",
    "check.separators": "Incluir separadores de página/diapositivo",
    "check.headings": "Detetar títulos automaticamente",
    "check.whitespace": "Normalizar espaços em branco",
    "check.optimize_ai": "Otimizar Markdown para leitura por IA",
    "check.subfolders": "Incluir subpastas",
    "check.overwrite": "Substituir ficheiros Markdown existentes",
    "check.header": "Incluir cabeçalho do documento",
    "check.toc": "Incluir índice",
    "check.images": "Extrair imagens incorporadas",
    "check.ocr": "Executar OCR em páginas de PDF digitalizadas",
    "check.comments": "Incluir comentários do documento",
    # Buttons
    "button.select_file": "Selecionar ficheiro...",
    "button.select_files": "Selecionar ficheiros...",
    "button.select_folder": "Selecionar pasta...",
    "button.save_as": "Guardar como...",
    "button.convert": "Converter",
    "button.cancel": "Cancelar",
    "button.open_output": "Abrir pasta de saída",
    "button.export_log": "Exportar registo",
    "button.clear": "Limpar",
    "button.dependencies": "Verificar / Instalar dependências",
    "button.exit": "Sair",
    # Status bar
    "status.ready": "Pronto.",
    "status.installing_deps": "A instalar dependências...",
    "status.deps_ready": "Dependências prontas.",
    "status.deps_warning": "A instalação de dependências terminou com avisos.",
    "status.deps_all_installed": "Todas as dependências estão instaladas.",
    "status.converting_init": "A converter 0 de {total} ficheiros...",
    "status.converting_file": "A converter {index} de {total}: {name}",
    "status.completed": "Concluído. {ok} com sucesso, {failed} com falha, {skipped} ignorados.",
    "status.failed": "A conversão falhou por completo.",
    "status.canceled": "Cancelado. {ok} convertidos antes de parar, {failed} com falha.",
    "status.canceling": "A cancelar após o ficheiro atual...",
    # Dialogs
    "dialog.missing_deps.title": "Dependências em falta",
    "dialog.missing_deps.body": (
        "Algumas dependências opcionais de conversão estão em falta:\n\n{list}\n\n"
        "Quer instalá-las automaticamente agora?"
    ),
    "dialog.deps.title": "Dependências",
    "dialog.deps.all_installed": "Todas as dependências de conversão já estão instaladas.",
    "dialog.install_deps.title": "Instalar dependências",
    "dialog.install_deps.body": (
        "As seguintes dependências estão em falta:\n\n{list}\n\n"
        "Quer instalá-las automaticamente agora?"
    ),
    "dialog.dep_install.title": "Instalação de dependências",
    "dialog.no_input.title": "Nenhuma entrada selecionada",
    "dialog.no_files.title": "Sem ficheiros para converter",
    "dialog.completed.title": "Conversão concluída",
    "dialog.failed.title": "Conversão falhada",
    "dialog.canceled.title": "Conversão cancelada",
    "dialog.open_output.title": "Abrir pasta de saída",
    "dialog.open_output.none": "Ainda não há nenhuma pasta de saída disponível.",
    "dialog.open_output.error": "Não foi possível abrir a pasta:\n{error}",
    "dialog.export_log.title": "Exportar registo",
    "dialog.export_log.empty": "O registo está vazio.",
    "dialog.export_log.error": "Não foi possível exportar o registo:\n{error}",
    # File dialogs
    "filedialog.select_document": "Selecionar documento",
    "filedialog.select_documents": "Selecionar documentos",
    "filedialog.select_folder": "Selecionar pasta",
    "filedialog.save_as": "Guardar ficheiro Markdown como",
    "filedialog.export_log": "Exportar registo para ficheiro",
    # Conversion summary
    "summary.total_found": "Total de ficheiros encontrados: {n}",
    "summary.jobs_created": "Total de tarefas criadas: {n}",
    "summary.succeeded": "Convertidos com sucesso: {n}",
    "summary.failed": "Conversões falhadas: {n}",
    "summary.skipped": "Ficheiros ignorados: {n}",
    "summary.output_header": "Pasta ou pastas de saída utilizadas:",
    "summary.no_output": "Não foram utilizadas pastas de saída.",
    # Validation and scan warnings
    "err.no_format": "Nenhum formato está selecionado. Ative pelo menos um formato.",
    "err.select_file": "Selecione um ficheiro para converter.",
    "err.file_missing": "O ficheiro não existe: {path}",
    "err.unsupported": "Tipo de ficheiro não suportado. Os ficheiros suportados são .pdf, .docx e .pptx.",
    "err.disabled_type": "O tipo de ficheiro selecionado está desativado na Seleção de formatos.",
    "err.no_output_path": "Nenhum caminho de saída selecionado no modo de ficheiro único.",
    "err.select_files": "Selecione um ou mais ficheiros para converter.",
    "err.select_folder": "Selecione uma pasta para converter.",
    "err.invalid_folder": "Pasta inválida: {path}",
    "warn.no_files_in_folder": "Não foram encontrados ficheiros na pasta selecionada.",
    "warn.no_supported_in_folder": "Não foram encontrados ficheiros suportados na pasta selecionada.",
    "warn.no_jobs": "Não foram criadas tarefas de conversão com as definições atuais de entrada e formato.",
    "warn.no_files_ready": "Não há ficheiros prontos para conversão.",
}
