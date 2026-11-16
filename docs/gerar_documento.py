"""Gera o documento de registro da Biblioteca Virtual Acervo no formato do formulário ACEX."""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
HEADER = ROOT / "_header.png"
FIG = ROOT / "figuras"
OUT = ROOT / "Documento_Registro_Biblioteca_Virtual_Acervo.pdf"
ARIAL = r"C:\Windows\Fonts\arial.ttf"
ARIALB = r"C:\Windows\Fonts\arialbd.ttf"
COUR = r"C:\Windows\Fonts\cour.ttf"

PAGE_W, PAGE_H = 595, 842
BOTTOM = 800
BLACK = (0, 0, 0)
PURPLE = (0.36, 0.32, 0.55)
LAVENDER = (0.93, 0.92, 0.98)
LAVENDER_H = (0.80, 0.78, 0.92)
CODE_BG = (0.96, 0.96, 0.95)


class Doc:
    def __init__(self):
        self.doc = pymupdf.open()
        self.reg = pymupdf.Font(fontfile=ARIAL)
        self.bold = pymupdf.Font(fontfile=ARIALB)
        self.cour = pymupdf.Font(fontfile=COUR)
        self.page = None
        self.y = 0
        self.new_page()

    def new_page(self):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page.insert_font(fontname="arial", fontfile=ARIAL)
        self.page.insert_font(fontname="arialbd", fontfile=ARIALB)
        self.page.insert_font(fontname="cour", fontfile=COUR)
        self.draw_header()
        self.y = 96
        return self.page

    def draw_header(self):
        page = self.page
        page.draw_rect(pymupdf.Rect(54, 14, 540, 76), color=BLACK, width=1.1)
        page.draw_line((190, 14), (190, 76), color=BLACK, width=1.1)
        logo = ROOT / "_logo.png"
        if logo.exists():
            page.insert_image(pymupdf.Rect(60, 20, 184, 70), filename=str(logo), keep_proportion=True)
        titles = [
            (32, 12.5, "ATIVIDADE CURRICULAR DE EXTENSÃO - ACEX"),
            (48, 11, "ENGENHARIA DE SOFTWARE - ADS"),
            (64, 11, "UNIPAR CASCAVEL - 2026"),
        ]
        for baseline, size, text in titles:
            width = self.length(text, "arialbd", size)
            self.page.insert_text((190 + (350 - width) / 2, baseline), text, fontname="arialbd", fontsize=size, color=BLACK)

    def length(self, text, font, size):
        face = {"arial": self.reg, "arialbd": self.bold, "cour": self.cour}[font]
        return face.text_length(text, fontsize=size)

    def wrap(self, text, font, size, width):
        if text == "":
            return [""]
        lines = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = ""
            for word in words:
                trial = word if not current else f"{current} {word}"
                if self.length(trial, font, size) <= width:
                    current = trial
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
        return lines

    def need(self, height):
        if self.y + height > BOTTOM:
            self.new_page()

    def put(self, x, y, text, font="arial", size=11, color=BLACK):
        self.page.insert_text((x, y), text, fontname=font, fontsize=size, color=color)

    def center(self, y, text, font="arialbd", size=13):
        width = self.length(text, font, size)
        self.put((PAGE_W - width) / 2, y, text, font, size)

    def heading(self, text, size=16, gap=18):
        self.need(gap + 8)
        self.y += 8
        self.put(54, self.y + size, text, "arialbd", size)
        self.y += size + gap

    def subhead(self, text, size=13):
        self.need(28)
        self.put(54, self.y + size, text, "arialbd", size)
        self.y += size + 10

    def paragraph(self, text, size=11, font="arial", indent=54, width=486, gap=4):
        lines = self.wrap(text, font, size, width)
        line_h = size + 3
        for line in lines:
            self.need(line_h)
            self.put(indent, self.y + size, line, font, size)
            self.y += line_h
        self.y += gap

    def bullets(self, items, size=11, indent=54, width=486):
        for item in items:
            lines = self.wrap("• " + item, "arial", size, width)
            line_h = size + 3
            for index, line in enumerate(lines):
                self.need(line_h)
                self.put(indent, self.y + size, line if index == 0 else "  " + line, "arial", size)
                self.y += line_h
        self.y += 4

    def field(self, label, value, first=False):
        label_lines = label if isinstance(label, list) else [label]
        value_lines = []
        for block in value.split("\n"):
            value_lines.extend(self.wrap(block, "arialbd", 11, 366))
        line_h = 13.2
        height = max(30, 12 + max(len(label_lines), len(value_lines)) * line_h)
        self._draw_field(label_lines, value_lines, height, line_h)

    def field_blocks(self, label, blocks):
        lines = []
        for block in blocks:
            if block == "":
                lines.append("")
            else:
                lines.extend(self.wrap(block, "arialbd", 11, 366))
        line_h = 13.2
        index = 0
        part = 0
        while index < len(lines):
            room = BOTTOM - self.y
            if room < 48:
                self.new_page()
                room = BOTTOM - self.y
            capacity = max(1, int((room - 14) / line_h))
            chunk = lines[index : index + capacity]
            height = 12 + len(chunk) * line_h
            shown = label if part == 0 else [""]
            self._draw_field(shown, chunk, height, line_h)
            index += len(chunk)
            part += 1

    def _draw_field(self, label_lines, value_lines, height, line_h):
        self.need(height)
        top = self.y
        rect = pymupdf.Rect(72, top, 540, top + height)
        self.page.draw_rect(rect, color=BLACK, width=0.8)
        self.page.draw_line((162, top), (162, top + height), color=BLACK, width=0.8)
        label_y = top + 16
        for line in label_lines:
            if line:
                self.put(78, label_y, line, "arial", 11)
            label_y += line_h
        value_y = top + 16
        for line in value_lines:
            if line:
                self.put(168, value_y, line, "arialbd", 11)
            value_y += line_h
        self.y = top + height

    def publico_row(self):
        height = 36
        self.need(height)
        top = self.y
        self.page.draw_rect(pymupdf.Rect(72, top, 540, top + height), color=BLACK, width=0.8)
        self.page.draw_line((162, top), (162, top + height), color=BLACK, width=0.8)
        self.page.draw_line((300, top), (300, top + height), color=BLACK, width=0.8)
        self.page.draw_line((378, top), (378, top + height), color=BLACK, width=0.8)
        self.put(78, top + 22, "Validar:", "arial", 11)
        self.put(168, top + 22, "( a preencher )", "arialbd", 11)
        self.put(308, top + 16, "Público", "arial", 11)
        self.put(308, top + 29, "Atendido:", "arial", 11)
        self.put(386, top + 22, "( X ) Interno   (   ) externo", "arialbd", 10)
        self.y = top + height

    def columns(self, headers, rows, widths, size=10.5):
        self.need(22)
        cursor = 54
        for header, width in zip(headers, widths):
            self.put(cursor, self.y + size, header, "arialbd", size)
            cursor += width
        self.y += size + 8
        for row in rows:
            wrapped = [self.wrap(cell, "arial", size, width - 8) for cell, width in zip(row, widths)]
            line_h = size + 3
            height = max(len(lines) for lines in wrapped) * line_h + 6
            self.need(height)
            cursor = 54
            for lines, width in zip(wrapped, widths):
                line_y = self.y + size
                for line in lines:
                    self.put(cursor, line_y, line, "arial", size)
                    line_y += line_h
                cursor += width
            self.y += height

    def code_block(self, lines):
        size = 9
        line_h = 12
        height = 10 + len(lines) * line_h
        self.need(height + 4)
        rect = pymupdf.Rect(54, self.y, 540, self.y + height)
        self.page.draw_rect(rect, color=(0.85, 0.85, 0.85), fill=CODE_BG, width=0.4)
        cursor = self.y + 14
        for line in lines:
            self.put(62, cursor, line, "cour", size, (0.1, 0.22, 0.18))
            cursor += line_h
        self.y += height + 8

    def image(self, path, caption, max_height=250):
        if not Path(path).exists():
            self.paragraph(f"[Imagem indisponível: {caption}]")
            return
        pix = pymupdf.Pixmap(str(path))
        if pix.alpha:
            pix = pymupdf.Pixmap(pix, 0)
        if pix.n > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        max_width = 470
        width = max_width
        height = width * pix.height / pix.width
        if height > max_height:
            height = max_height
            width = height * pix.width / pix.height
        self.need(height + 8)
        x = 54 + (486 - width) / 2
        rect = pymupdf.Rect(x, self.y, x + width, self.y + height)
        self.page.insert_image(rect, stream=pix.tobytes("jpeg", jpg_quality=62), keep_proportion=True)
        self.page.draw_rect(rect, color=(0.75, 0.75, 0.75), width=0.6)
        self.y += height + 8
        self.paragraph(caption, size=11)

    def save(self):
        self.doc.save(OUT)
        self.doc.close()


def entity(page, x, y, w, title, fields):
    row_h = 13
    height = 18 + row_h * len(fields)
    page.draw_rect(pymupdf.Rect(x, y, x + w, y + height), color=PURPLE, fill=LAVENDER, width=0.9)
    page.draw_rect(pymupdf.Rect(x, y, x + w, y + 18), color=PURPLE, fill=LAVENDER_H, width=0.9)
    page.insert_text((x + 6, y + 13), title, fontname="arialbd", fontsize=8, color=PURPLE)
    cursor = y + 18
    for field_name in fields:
        page.draw_line((x, cursor + row_h), (x + w, cursor + row_h), color=(0.78, 0.76, 0.88), width=0.4)
        page.insert_text((x + 6, cursor + 10), field_name, fontname="arial", fontsize=7, color=BLACK)
        cursor += row_h
    return pymupdf.Rect(x, y, x + w, y + height)


def connect(page, a, b, label=""):
    start = pymupdf.Point((a.x0 + a.x1) / 2, a.y1)
    end = pymupdf.Point((b.x0 + b.x1) / 2, b.y0)
    if abs(start.x - end.x) < 8:
        page.draw_line(start, end, color=PURPLE, width=0.8)
    else:
        mid_y = (start.y + end.y) / 2
        page.draw_line(start, pymupdf.Point(start.x, mid_y), color=PURPLE, width=0.8)
        page.draw_line(pymupdf.Point(start.x, mid_y), pymupdf.Point(end.x, mid_y), color=PURPLE, width=0.8)
        page.draw_line(pymupdf.Point(end.x, mid_y), end, color=PURPLE, width=0.8)
    if label:
        page.insert_text(((start.x + end.x) / 2 + 4, (start.y + end.y) / 2), label, fontname="arial", fontsize=7, color=PURPLE)


def side_connect(page, a, b, label=""):
    start = pymupdf.Point(a.x1, (a.y0 + a.y1) / 2)
    end = pymupdf.Point(b.x0, (b.y0 + b.y1) / 2)
    page.draw_line(start, end, color=PURPLE, width=0.8)
    if label:
        page.insert_text(((start.x + end.x) / 2 - 18, start.y - 8), label, fontname="arial", fontsize=7, color=PURPLE)


def flow_box(page, x, y, w, h, text, diamond=False):
    rect = pymupdf.Rect(x, y, x + w, y + h)
    if diamond:
        cx, cy = x + w / 2, y + h / 2
        shape = page.new_shape()
        shape.draw_polyline(
            [pymupdf.Point(cx, y), pymupdf.Point(x + w, cy), pymupdf.Point(cx, y + h), pymupdf.Point(x, cy)]
        )
        shape.finish(color=PURPLE, fill=(0.97, 0.95, 0.90), closePath=True, width=0.9)
        shape.commit()
        # The label sits in the wide middle. The top of the diamond is too narrow for the phrase.
        inner_w = w * 0.46
        page.insert_textbox(
            pymupdf.Rect(cx - inner_w / 2, cy - 7, cx + inner_w / 2, cy + 9),
            text, fontname="arial", fontsize=8, align=1, color=BLACK,
        )
    else:
        page.draw_rect(rect, color=PURPLE, fill=LAVENDER, width=0.8, radius=0.04)
        page.insert_textbox(
            pymupdf.Rect(x + 8, y + (h - 12) / 2, x + w - 8, y + (h + 12) / 2),
            text, fontname="arial", fontsize=8, align=1, color=BLACK,
        )
    return rect


def arrow(page, a, b):
    page.draw_line(pymupdf.Point(a.x1, (a.y0 + a.y1) / 2), pymupdf.Point(b.x0, (b.y0 + b.y1) / 2), color=PURPLE, width=0.8)


def down_arrow(page, a, b):
    page.draw_line(pymupdf.Point((a.x0 + a.x1) / 2, a.y1), pymupdf.Point((b.x0 + b.x1) / 2, b.y0), color=PURPLE, width=0.8)


def build():
    doc = Doc()
    doc.center(112, "DOCUMENTO PARA REGISTRO DE ATIVIDADE DE EXTENSÃO", size=12)
    doc.y = 126

    doc.field("Projeto:", "BIBLIOTECA VIRTUAL ACERVO")
    doc.publico_row()
    doc.field(["Ação", "Desenvolvida:"], "J Implementação de Software")
    doc.field("Integrantes", "David Aparecido dos Santos Hotes - RA: 60023925")
    doc.field(["Professor", "coordenador:"], "Luiz Fernando R. da Silva")
    doc.field(["Título da", "Atividade:"], "Biblioteca Virtual Acervo")
    doc.field(
        ["Resumo da", "Atividade:"],
        "O Acervo é um sistema web de biblioteca para uma instituição de ensino. "
        "O aluno cria a própria conta com nome, matrícula, e-mail e senha, consulta o catálogo, "
        "vê quantos exemplares estão disponíveis e solicita empréstimo. A solicitação não retira o livro. "
        "Um professor ou administrador aprova, reserva um exemplar e, na retirada, registra o empréstimo. "
        "A devolução pedida pelo aluno fica aguardando confirmação. O exemplar só volta à estante quando "
        "a biblioteca confirma o recebimento. O sistema separa a área do aluno da área administrativa, "
        "guarda senhas com hash e registra as movimentações. A obra bibliográfica é distinta dos exemplares "
        "físicos. A interface foi feita em React e TypeScript. A API foi feita em Django e Django REST Framework, "
        "com SQLite no desenvolvimento e configuração pronta para PostgreSQL.",
    )
    doc.field(["Local ou", "Demandante:"], "Desenvolvimento para uso institucional, com banco local na fase inicial.")
    doc.field(
        "Objetivos:",
        "1. Objetivo Geral: Centralizar o acervo e o ciclo de empréstimo para que o aluno consulte a biblioteca "
        "sem assumir o controle da devolução física, e para que a equipe administre livros, alunos e movimentações "
        "com registro de quem confirmou cada ato.\n"
        "2. Objetivo Específico 1: Permitir o cadastro real do aluno, com matrícula única, e-mail válido, "
        "confirmação de senha e senha armazenada com hash.\n"
        "3. Objetivo Específico 2: Autenticar aluno e administrador em entradas separadas, proteger rotas e encerrar a sessão.\n"
        "4. Objetivo Específico 3: Diferenciar a obra dos exemplares físicos e calcular a disponibilidade a partir desses exemplares.\n"
        "5. Objetivo Específico 4: Conduzir solicitação, aprovação, retirada, pedido de devolução e confirmação administrativa "
        "sem que o aluno consiga encerrar o empréstimo sozinho.\n"
        "6. Objetivo Específico 5: Avisar alunos e administradores sobre aprovação, recusa, retirada, prazo, atraso e devolução.",
    )
    doc.field(
        "Etapas:",
        "O trabalho começou pelo planejamento da arquitetura e pela modelagem do banco, separando usuário, aluno, "
        "obra, exemplar, solicitação, empréstimo, notificação e histórico. Em seguida foi construído o backend, "
        "com autenticação, validações e as regras de circulação dentro de transação. Depois foram desenvolvidas "
        "a área do aluno e a área administrativa, ambas ligadas à mesma API. Por fim entraram as notificações, "
        "a documentação, os testes automatizados e a conferência do fluxo no navegador.",
    )
    doc.field_blocks(
        ["Resultados", "Alcançados:"],
        [
            "Funcionalidades implementadas",
            "O sistema foi desenvolvido e inclui as seguintes funcionalidades:",
            "",
            "Área do aluno",
            "• Cadastro com nome, matrícula única, e-mail, senha e confirmação de senha",
            "• Recusa de matrícula ou e-mail já usados, com mensagem clara",
            "• Login por matrícula e senha, logout e recuperação de senha por código temporário",
            "• Painel com saudação, livros disponíveis, empréstimos ativos, solicitações e destaques",
            "• Catálogo com capa, ficha, pesquisa, filtros, ordenação e paginação",
            "• Solicitação de empréstimo sem dar baixa no exemplar",
            "• Acompanhamento dos status Pendente, Aprovado, Emprestado, Aguardando confirmação, Devolvido, Atrasado e Recusado",
            "• Pedido de devolução que não libera o exemplar",
            "",
            "Área administrativa",
            "• Painel com totais de livros, exemplares, disponíveis, emprestados, solicitações, devoluções, atrasos e alunos",
            "• Cadastro, edição e exclusão de livros, capas, categorias e quantidade de exemplares",
            "• Bloqueio da exclusão quando há empréstimo, reserva ou histórico",
            "• Consulta de alunos, edição de nome e e-mail, bloqueio e desbloqueio, sem exibir senha",
            "• Aprovação que reserva um exemplar e recusa com motivo",
            "• Registro da retirada e empréstimo direto no balcão",
            "• Alteração de prazo com motivo e histórico da mudança",
            "• Confirmação da devolução somente pelo administrador, com nome de quem confirmou",
            "• Notificações com leitura e histórico de movimentações",
        ],
    )
    doc.field(
        ["Quantidade de", "Público", "Atingido:"],
        "A validação deste desenvolvimento usou testes automatizados e um percurso manual no navegador. "
        "A quantidade de pessoas alcançadas deve ser preenchida pela instituição quando a atividade for apresentada. "
        "O sistema está pronto para uso interno da biblioteca e dos alunos.",
    )

    doc.heading("APRESENTAÇÃO DAS EVIDÊNCIAS", size=14, gap=14)
    doc.heading("LEVANTAMENTO DE REQUISITOS", size=15, gap=12)
    doc.subhead("Requisitos Funcionais")
    functional = [
        ("RF-001", "Cadastro do aluno", "Registrar nome, matrícula única, e-mail válido, senha e confirmação", "Alta"),
        ("RF-002", "Login do aluno", "Autenticar por matrícula e senha e manter a sessão", "Alta"),
        ("RF-003", "Login administrativo", "Autenticar professor ou administrador por e-mail e senha", "Alta"),
        ("RF-004", "Recuperação de senha", "Emitir código temporário e permitir a troca", "Alta"),
        ("RF-005", "Painel do aluno", "Mostrar saudação, contadores, destaques e movimentação recente", "Média"),
        ("RF-006", "Catálogo", "Listar obras com pesquisa, filtros, ordenação e paginação", "Alta"),
        ("RF-007", "Detalhe da obra", "Exibir a ficha e a situação dos exemplares", "Alta"),
        ("RF-008", "Solicitar empréstimo", "Registrar pedido sem dar baixa no exemplar", "Alta"),
        ("RF-009", "Acompanhar locações", "Listar solicitações e empréstimos com o status de cada um", "Alta"),
        ("RF-010", "Pedir devolução", "Marcar o empréstimo como aguardando confirmação", "Alta"),
        ("RF-011", "Painel administrativo", "Exibir os indicadores gerais da biblioteca", "Média"),
        ("RF-012", "Gerir livros", "Incluir, alterar, excluir e controlar exemplares e capas", "Alta"),
        ("RF-013", "Gerir categorias", "Incluir e remover categorias sem livros vinculados", "Média"),
        ("RF-014", "Gerir alunos", "Consultar, editar dados permitidos e bloquear contas", "Alta"),
        ("RF-015", "Analisar solicitações", "Aprovar com reserva ou recusar com motivo", "Alta"),
        ("RF-016", "Registrar retirada", "Criar o empréstimo e marcar o exemplar como emprestado", "Alta"),
        ("RF-017", "Acompanhar empréstimos", "Filtrar ativos, atrasados e devolvidos e alterar prazos", "Alta"),
        ("RF-018", "Confirmar devolução", "Concluir a devolução somente pela administração", "Alta"),
        ("RF-019", "Notificações", "Avisar as partes e guardar o estado de leitura", "Média"),
        ("RF-020", "Histórico", "Registrar ações administrativas e movimentações", "Alta"),
    ]
    doc.columns(["ID", "Requisito", "Descrição", "Prioridade"], functional, [62, 130, 230, 70])

    doc.y += 8
    doc.subhead("Requisitos Não-Funcionais")
    nonfunctional = [
        ("RNF-001", "Segurança da senha", "Senha armazenada com hash e nunca devolvida pela API", "Alta"),
        ("RNF-002", "Autorização", "Rotas de aluno e de administração separadas no cliente e no servidor", "Alta"),
        ("RNF-003", "Integridade", "Mudanças de exemplar e de empréstimo feitas em transação", "Alta"),
        ("RNF-004", "Concorrência", "Duas aprovações não reservam o mesmo último exemplar", "Alta"),
        ("RNF-005", "Usabilidade", "Interface clara, com retorno visual de sucesso e de erro", "Alta"),
        ("RNF-006", "Responsividade", "Uso em computador, tablet e celular", "Média"),
        ("RNF-007", "Persistência", "SQLite no desenvolvimento e configuração pronta para PostgreSQL", "Alta"),
        ("RNF-008", "Rastreio", "Cada confirmação guarda o administrador responsável", "Alta"),
        ("RNF-009", "Sessão", "Token de acesso com renovação e encerramento no logout", "Alta"),
        ("RNF-010", "Manutenção", "Regras no servidor, separadas das telas", "Média"),
    ]
    doc.columns(["ID", "Requisito", "Descrição", "Prioridade"], nonfunctional, [70, 120, 240, 70])

    doc.heading("DIAGRAMAS E PROTÓTIPOS", size=15, gap=10)
    doc.subhead("Diagrama Entidade-Relacionamento (DER)")
    doc.paragraph(
        "O diagrama da página seguinte mostra as entidades do Acervo. A obra não é o exemplar: um livro pode ter vários exemplares, cada um com código e situação próprios. O pedido aponta para a obra e, depois da aprovação, para um exemplar reservado. O empréstimo aponta para um exemplar específico."
    )

    doc.new_page()
    page = doc.page
    page.insert_text((54, 104), "Diagrama Entidade-Relacionamento (DER)", fontname="arialbd", fontsize=13, color=BLACK)

    def rule(x1, y1, x2, y2):
        page.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2), color=PURPLE, width=0.9)

    def mark(x, y, text, align="left"):
        size = 8
        width = pymupdf.Font(fontfile=ARIAL).text_length(text, fontsize=size)
        x0 = x - width if align == "right" else x
        page.draw_rect(pymupdf.Rect(x0 - 1, y - 9, x0 + width + 2, y + 2), color=(1, 1, 1), fill=(1, 1, 1), width=0)
        page.insert_text((x0, y), text, fontname="arial", fontsize=size, color=PURPLE)

    user = entity(page, 36, 118, 140, "USER", ["int   id   PK", "string   email   UK", "string   full_name", "string   role", "string   password_hash"])
    student = entity(page, 268, 118, 150, "STUDENT_PROFILE", ["int   id   PK", "int   user_id   FK", "string   enrollment   UK", "bool   is_blocked", "date   created_at"])
    category = entity(page, 448, 118, 112, "CATEGORY", ["int   id   PK", "string   name   UK", "string   description"])
    book = entity(page, 442, 255, 118, "BOOK", ["int   id   PK", "int   category_id   FK", "string   title", "string   author", "string   isbn", "int   year"])
    copy = entity(page, 442, 430, 118, "COPY", ["int   id   PK", "int   book_id   FK", "string   inventory_code   UK", "string   status"])
    request = entity(page, 36, 330, 145, "LOAN_REQUEST", ["int   id   PK", "int   student_id   FK", "int   book_id   FK", "int   copy_id   FK", "string   status"])
    loan = entity(page, 268, 322, 150, "LOAN", ["int   id   PK", "int   student_id   FK", "int   copy_id   FK", "date   due_date", "string   status", "int   confirmed_by   FK"])
    note = entity(page, 36, 530, 150, "NOTIFICATION", ["int   id   PK", "int   user_id   FK", "string   kind", "bool   is_read"])
    user_y = (user.y0 + user.y1) / 2
    rule(user.x1, user_y, student.x0, user_y)
    mark(user.x1 + 8, user_y - 4, "1")
    mark(student.x0 - 6, user_y - 4, "0 ou 1", "right")
    cat_x = (category.x0 + category.x1) / 2
    book_x = (book.x0 + book.x1) / 2
    rule(cat_x, category.y1, book_x, book.y0)
    mark(book_x + 8, category.y1 + 16, "1")
    mark(book_x + 8, book.y0 - 4, "N")
    copy_x = (copy.x0 + copy.x1) / 2
    rule(book_x, book.y1, copy_x, copy.y0)
    mark(copy_x + 8, book.y1 + 16, "1")
    mark(copy_x + 8, copy.y0 - 4, "N")
    stu_x = (student.x0 + student.x1) / 2
    loan_x = (loan.x0 + loan.x1) / 2
    rule(stu_x, student.y1, loan_x, loan.y0)
    mark(stu_x + 8, student.y1 + 16, "1")
    mark(loan_x + 8, loan.y0 - 4, "N")
    req_x = (request.x0 + request.x1) / 2
    branch_x = student.x0 + 18
    branch_y = (student.y1 + request.y0) / 2
    rule(branch_x, student.y1, branch_x, branch_y)
    rule(branch_x, branch_y, req_x, branch_y)
    rule(req_x, branch_y, req_x, request.y0)
    mark(branch_x + 6, student.y1 + 16, "1")
    mark(req_x + 6, request.y0 - 4, "N")
    link_y = (request.y0 + request.y1) / 2
    rule(request.x1, link_y, loan.x0, link_y)
    mark(request.x1 + 6, link_y - 11, "0 ou 1")
    mark(loan.x0 - 6, link_y - 11, "0 ou 1", "right")
    rule(user.x0, user_y, 24, user_y)
    rule(24, user_y, 24, (note.y0 + note.y1) / 2)
    rule(24, (note.y0 + note.y1) / 2, note.x0, (note.y0 + note.y1) / 2)
    mark(28, user.y1 + 12, "1")
    mark(30, note.y0 - 4, "N")
    doc.y = 618
    doc.paragraph(
        "Diagrama entidade-relacionamento das tabelas de conta, aluno, categoria, obra, exemplar, solicitação, empréstimo e notificação."
    )
    doc.paragraph("Descrição: O diagrama apresenta as entidades principais:")
    doc.bullets(
        [
            "USER: conta de acesso, com e-mail único, perfil e senha armazenada com hash.",
            "STUDENT_PROFILE: matrícula única e situação de bloqueio do aluno.",
            "CATEGORY e BOOK: classificação e ficha da obra.",
            "COPY: exemplar físico, com código próprio e situação.",
            "LOAN_REQUEST: pedido do aluno, que ainda não retira o livro.",
            "LOAN: retirada registrada, prazo, status e administrador que confirmou a devolução.",
            "NOTIFICATION: aviso com controle de leitura.",
        ]
    )
    doc.paragraph(
        "Um aluno pode ter vários pedidos e vários empréstimos. Um exemplar pode ter vários empréstimos no histórico, mas apenas um empréstimo aberto."
    )

    doc.new_page()
    page = doc.page
    page.insert_text((54, 104), "Diagrama de Classes", fontname="arialbd", fontsize=13, color=BLACK)

    def rule(x1, y1, x2, y2):
        page.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2), color=PURPLE, width=0.9)

    def mark(x, y, text, align="left"):
        size = 8
        width = pymupdf.Font(fontfile=ARIAL).text_length(text, fontsize=size)
        x0 = x - width if align == "right" else x
        page.draw_rect(pymupdf.Rect(x0 - 1, y - 9, x0 + width + 2, y + 2), color=(1, 1, 1), fill=(1, 1, 1), width=0)
        page.insert_text((x0, y), text, fontname="arial", fontsize=size, color=PURPLE)

    service = entity(
        page, 188, 116, 220, "CirculationService",
        ["+ request_loan()", "+ approve_request()", "+ reject_request()", "+ register_loan()", "+ request_return()", "+ confirm_return()"],
    )
    user = entity(page, 32, 300, 140, "User", ["- email", "- full_name", "- role", "+ set_password()"])
    student = entity(page, 268, 300, 152, "StudentProfile", ["- enrollment", "- is_blocked", "+ block()", "+ unblock()"])
    book = entity(page, 448, 292, 112, "Book", ["- title", "- author", "- isbn", "- year"])
    copy = entity(page, 448, 448, 112, "Copy", ["- inventory_code", "- status", "+ reserve()", "+ release()"])
    loan = entity(page, 268, 508, 152, "Loan", ["- status", "- due_date", "- confirmed_by", "+ request_return()", "+ confirm()"])
    request = entity(page, 32, 520, 150, "LoanRequest", ["- status", "- requested_at", "+ approve()", "+ reject()"])
    svc_x = (service.x0 + service.x1) / 2
    stu_x = (student.x0 + student.x1) / 2
    book_x = (book.x0 + book.x1) / 2
    bus_y = 268
    rule(svc_x, service.y1, svc_x, bus_y)
    rule(svc_x, bus_y, stu_x, bus_y)
    rule(stu_x, bus_y, stu_x, student.y0)
    rule(svc_x, bus_y, book_x, bus_y)
    rule(book_x, bus_y, book_x, book.y0)
    mark(svc_x + 8, bus_y - 5, "gerencia")
    user_y = (user.y0 + user.y1) / 2
    rule(user.x1, user_y, student.x0, user_y)
    mark(user.x1 + 8, user_y - 4, "1")
    mark(student.x0 - 6, user_y - 4, "0 ou 1", "right")
    copy_x = (copy.x0 + copy.x1) / 2
    rule(book_x, book.y1, copy_x, copy.y0)
    mark(copy_x + 8, book.y1 + 16, "1")
    mark(copy_x + 8, copy.y0 - 4, "N")
    loan_x = (loan.x0 + loan.x1) / 2
    rule(stu_x, student.y1, loan_x, loan.y0)
    mark(stu_x + 8, student.y1 + 16, "1")
    mark(loan_x + 8, loan.y0 - 4, "N")
    link_y = (request.y0 + min(request.y1, loan.y1)) / 2
    rule(request.x1, link_y, loan.x0, link_y)
    mark(request.x1 + 6, link_y - 11, "0 ou 1")
    mark(loan.x0 - 6, link_y - 11, "0 ou 1", "right")
    doc.y = 620
    doc.paragraph("Diagrama de classes das entidades de conta, acervo e circulação, e do serviço que aplica as regras.")
    doc.paragraph("Descrição: O diagrama de classes apresenta:")
    doc.bullets(
        [
            "User: identidade de acesso e perfil aluno ou administrador.",
            "StudentProfile: matrícula e bloqueio. A matrícula não é editável pelo aluno.",
            "Book: ficha da obra. Copy: unidade física e sua situação.",
            "LoanRequest e Loan: pedido e empréstimo, com status próprios.",
            "CirculationService: solicita, aprova, registra a retirada, pede devolução e confirma.",
        ]
    )
    doc.paragraph("As telas chamam a API. A API chama o serviço. O serviço é quem altera exemplar, pedido e empréstimo na mesma transação.")

    doc.new_page()
    page = doc.page
    page.insert_text((54, 100), "Diagrama de Fluxo de Processos", fontname="arialbd", fontsize=13, color=BLACK)

    def rule(x1, y1, x2, y2):
        page.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(x2, y2), color=PURPLE, width=0.9)

    solicita = flow_box(page, 190, 112, 180, 30, "Aluno solicita a obra")
    decide = flow_box(page, 155, 154, 250, 56, "Há exemplar e limite?", True)
    recusa_hora = flow_box(page, 430, 166, 128, 32, "Recusado na hora")
    pendente = flow_box(page, 210, 224, 140, 28, "Pedido pendente")
    recusa = flow_box(page, 40, 276, 130, 28, "Administrador recusa")
    aprova = flow_box(page, 210, 276, 140, 28, "Administrador aprova")
    reserva = flow_box(page, 400, 276, 135, 28, "Exemplar reservado")
    retirada = flow_box(page, 210, 328, 140, 28, "Retirada registrada")
    emprestado = flow_box(page, 200, 378, 160, 28, "Exemplar emprestado")
    pede = flow_box(page, 36, 440, 145, 32, "Aluno pede devolução")
    aguarda = flow_box(page, 198, 440, 164, 32, "Aguardando confirmação")
    balcao = flow_box(page, 390, 440, 145, 32, "Entrega no balcão")
    confirma = flow_box(page, 185, 508, 190, 30, "Administrador confirma")
    livre = flow_box(page, 200, 562, 160, 28, "Exemplar disponível")
    down_arrow(page, solicita, decide)
    arrow(page, decide, recusa_hora)
    page.insert_text((decide.x1 + 4, (decide.y0 + decide.y1) / 2 - 8), "não", fontname="arial", fontsize=8, color=PURPLE)
    down_arrow(page, decide, pendente)
    page.insert_text(((pendente.x0 + pendente.x1) / 2 + 6, decide.y1 + 11), "sim", fontname="arial", fontsize=8, color=PURPLE)
    down_arrow(page, pendente, aprova)
    rule(pendente.x0, (pendente.y0 + pendente.y1) / 2, recusa.x1, (recusa.y0 + recusa.y1) / 2)
    arrow(page, aprova, reserva)
    down_arrow(page, aprova, retirada)
    down_arrow(page, retirada, emprestado)
    rule((emprestado.x0 + emprestado.x1) / 2, emprestado.y1, (aguarda.x0 + aguarda.x1) / 2, aguarda.y0)
    rule(emprestado.x1, (emprestado.y0 + emprestado.y1) / 2, (balcao.x0 + balcao.x1) / 2, (emprestado.y0 + emprestado.y1) / 2)
    rule((balcao.x0 + balcao.x1) / 2, (emprestado.y0 + emprestado.y1) / 2, (balcao.x0 + balcao.x1) / 2, balcao.y0)
    arrow(page, pede, aguarda)
    down_arrow(page, aguarda, confirma)
    rule((balcao.x0 + balcao.x1) / 2, balcao.y1, (balcao.x0 + balcao.x1) / 2, (balcao.y1 + confirma.y0) / 2)
    rule((balcao.x0 + balcao.x1) / 2, (balcao.y1 + confirma.y0) / 2, confirma.x1, (confirma.y0 + confirma.y1) / 2)
    down_arrow(page, confirma, livre)
    doc.y = 608
    doc.paragraph(
        "Diagrama de fluxo da solicitação, da aprovação, da retirada e da devolução. A seta da entrega no balcão cobre o caso em que o aluno devolve o livro sem ter pedido antes pelo sistema."
    )
    doc.paragraph("Descrição: O fluxo apresenta:")
    doc.bullets(
        [
            "Solicitação: o sistema verifica exemplar, pedido duplicado e limite antes de gravar.",
            "Aprovação: reserva um exemplar disponível. A recusa não mexe no exemplar.",
            "Retirada: cria o empréstimo e marca o exemplar como emprestado.",
            "Devolução: o pedido do aluno só muda o status para aguardando confirmação.",
            "Confirmação: somente o administrador conclui a devolução e libera o exemplar.",
        ]
    )

    if doc.y > 620:
        doc.new_page()
    doc.heading("Protótipos de Interface", size=14, gap=8)

    shots = [
        (
            "Entrada do aluno",
            FIG / "aluno-entrar.png",
            "Tela de entrada do aluno, com matrícula, senha, recuperação de senha e link de cadastro. A área da biblioteca fica em outro endereço.",
            ["Formulário separado do acesso administrativo", "Mensagem do servidor quando a credencial é inválida", "Link para cadastro e para recuperação de senha"],
            230,
        ),
        (
            "Início do aluno",
            FIG / "aluno-inicio.png",
            "Painel do aluno com saudação pelo nome, indicadores da própria conta e destaques do acervo.",
            ["Saudação com o nome do aluno", "Contadores de livros, empréstimos, solicitações e histórico", "Capas e situação de disponibilidade"],
            230,
        ),
        (
            "Catálogo",
            FIG / "aluno-catalogo.png",
            "Catálogo com pesquisa por título, autor e ISBN, filtro de categoria e de disponibilidade, ordenação e a fração de exemplares livres.",
            ["Grade de obras com capa, autor, ano e categoria", "Filtros e ordenação alfabética", "Indicação de quantos exemplares estão disponíveis"],
            240,
        ),
        (
            "Meus empréstimos",
            FIG / "aluno-emprestimos.png",
            "Acompanhamento do aluno. O único ato sobre um livro emprestado é solicitar a devolução. A conclusão aparece como devolvido somente depois da confirmação da biblioteca.",
            ["Filtros por situação", "Botão Solicitar devolução, sem botão de confirmar", "Registro de quem confirmou a devolução no histórico"],
            240,
        ),
        (
            "Painel administrativo",
            FIG / "admin-painel.png",
            "Painel da biblioteca com os totais do acervo, barras de situação e as filas de solicitação e atraso.",
            ["Cartões de livros, exemplares, disponíveis, emprestados, solicitações, devoluções, atrasos e alunos", "Barras comparando a situação do acervo", "Acesso direto às filas"],
            240,
        ),
        (
            "Página de livros",
            FIG / "admin-livros.png",
            "Gestão do acervo, com busca, cadastro, edição, exclusão e a relação entre exemplares totais e disponíveis.",
            ["Tabela com título, autor, categoria, exemplares e situação", "Cadastro de livro e controle de quantidade", "Exclusão bloqueada quando existe movimentação vinculada"],
            240,
        ),
        (
            "Página de alunos",
            FIG / "admin-alunos.png",
            "Consulta dos alunos cadastrados. A senha não aparece. A matrícula não é alterada por esta tela.",
            ["Busca por nome, matrícula ou e-mail", "Situação da conta e quantidade de empréstimos", "Detalhe com histórico individual, bloqueio e desbloqueio"],
            200,
        ),
        (
            "Página de empréstimos",
            FIG / "admin-emprestimos.png",
            "Acompanhamento das retiradas. A confirmação da devolução e a alteração de prazo ficam nesta área, exclusivas da administração.",
            ["Filtros de em aberto, aguardando confirmação, atrasados e devolvidos", "Botão Confirmar devolução somente para o administrador", "Alteração de prazo e empréstimo direto no balcão"],
            220,
        ),
    ]
    for title, path, caption, points, height in shots:
        doc.subhead(title)
        doc.image(path, caption, max_height=height)
        doc.paragraph("Características:")
        doc.bullets(points)

    doc.heading("BUGS CORRIGIDOS", size=16, gap=12)

    doc.subhead("Bug 1: Permissão do catálogo")
    doc.paragraph(
        "Problema: A listagem de livros montava a permissão juntando objetos já criados. A composição só funciona entre as classes, e a consulta de quem já estava autenticado quebrava."
    )
    doc.paragraph("Solução: Compor as classes de permissão e só então criar o objeto usado pela API.")
    doc.paragraph("Python")
    doc.code_block(
        [
            "def get_permissions(self):",
            "    if self.request.method == \"GET\":",
            "        return [(IsStudentRole | IsAdminRole)()]",
            "    return [IsAdminRole()]",
        ]
    )

    doc.subhead("Bug 2: Contadores do painel do aluno")
    doc.paragraph(
        "Problema: O painel lia empréstimos e solicitações antes de buscá-los no banco, então a saudação e os números não saíam."
    )
    doc.paragraph("Solução: Buscar as listas antes de calcular os contadores.")
    doc.paragraph("Python")
    doc.code_block(
        [
            "loans = loan_queryset().filter(student=student)",
            "requests = request_queryset().filter(student=student)",
            "active = loans.filter(status__in=Loan.OPEN)",
        ]
    )

    doc.subhead("Bug 3: Confirmação de devolução pelo aluno")
    doc.paragraph(
        "Problema: Uma chamada autenticada como aluno não pode concluir a devolução nem liberar o exemplar, mesmo que o corpo da requisição tente escolher o status final."
    )
    doc.paragraph(
        "Solução: A rota de confirmação existe apenas na área administrativa. O pedido do aluno grava somente aguardando confirmação e mantém o exemplar emprestado. O teste automatizado recusou a confirmação feita com o token do aluno e conferiu que a situação do exemplar não mudou."
    )

    doc.y += 6
    doc.paragraph("Aplicação local: http://127.0.0.1:5173")
    doc.paragraph("API local: http://127.0.0.1:8000")
    doc.paragraph("Repositório: https://github.com/David-IFPR/biblioteca-virtual")

    doc.save()
    print(OUT)


if __name__ == "__main__":
    build()
