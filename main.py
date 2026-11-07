import ast
import operator as op
import re

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

Window.clearcolor = (0.08, 0.08, 0.1, 1)

OPERATORS = "+−×÷^"

BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
}
UNARY_OPS = {ast.USub: op.neg, ast.UAdd: op.pos}


def safe_eval(expression):
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent too large")
            return BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
            return UNARY_OPS[type(node.op)](_eval(node.operand))
        raise ValueError("Invalid expression")

    return _eval(ast.parse(expression, mode="eval"))


def format_result(value):
    if isinstance(value, complex):
        raise ValueError("Complex result")
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Out of range")
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return format(value, ".10g")
    return str(value)


def to_python(expr):
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    expr = expr.replace("^", "**").replace("%", "/100")
    expr = re.sub(r"(\d|\))\s*\(", r"\1*(", expr)
    return expr


class Calculator(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kwargs)
        self.expr = ""
        self.last_result = ""
        self.error = False

        self.history = Label(
            text="", font_size="18sp", color=(0.6, 0.6, 0.65, 1),
            size_hint_y=0.07, halign="right", valign="middle",
        )
        self.history.bind(size=lambda w, s: setattr(w, "text_size", s))

        self.display = Label(
            text="0", font_size="52sp", color=(1, 1, 1, 1),
            size_hint_y=0.2, halign="right", valign="middle",
        )
        self.display.bind(size=lambda w, s: setattr(w, "text_size", s))

        self.add_widget(self.history)
        self.add_widget(self.display)

        rows = [
            ["C", "DEL", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["(", ")", "^", "."],
        ]
        grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=0.6)
        for row in rows:
            for key in row:
                grid.add_widget(self.make_button(key))
        self.add_widget(grid)

        bottom = BoxLayout(spacing=dp(8), size_hint_y=0.13)
        bottom.add_widget(self.make_button("0"))
        bottom.add_widget(self.make_button("="))
        self.add_widget(bottom)

    def make_button(self, key):
        if key == "=":
            color = (0.95, 0.55, 0.1, 1)
        elif key in OPERATORS or key == "%":
            color = (0.25, 0.4, 0.75, 1)
        elif key in ("C", "DEL"):
            color = (0.75, 0.25, 0.25, 1)
        elif key in ("(", ")"):
            color = (0.3, 0.3, 0.38, 1)
        else:
            color = (0.18, 0.18, 0.22, 1)
        btn = Button(
            text=key, font_size="26sp", background_normal="",
            background_color=color, color=(1, 1, 1, 1),
        )
        btn.bind(on_release=lambda b: self.on_key(key))
        return btn

    def refresh(self):
        text = self.expr if self.expr else "0"
        self.display.text = text
        n = len(text)
        self.display.font_size = "52sp" if n <= 9 else "38sp" if n <= 14 else "26sp"

    def current_number(self):
        parts = re.split(r"[+−×÷^()%]", self.expr)
        return parts[-1] if parts else ""

    def on_key(self, key):
        if self.error:
            self.expr, self.error = "", False
            self.history.text = ""
            if key in ("C", "DEL"):
                self.refresh()
                return

        if key == "C":
            self.expr = ""
            self.history.text = ""
        elif key == "DEL":
            self.expr = self.expr[:-1]
        elif key == "=":
            self.calculate()
            return
        elif key.isdigit():
            if self.expr.endswith(")") or self.expr.endswith("%"):
                self.expr += "×"
            self.expr += key
        elif key == ".":
            if "." not in self.current_number():
                if not self.current_number():
                    self.expr += "0"
                self.expr += "."
        elif key in OPERATORS:
            self.add_operator(key)
        elif key == "%":
            if self.expr and (self.expr[-1].isdigit() or self.expr[-1] in ")%"):
                self.expr += "%"
        elif key == "(":
            if self.expr and (self.expr[-1].isdigit() or self.expr[-1] in ")%"):
                self.expr += "×"
            self.expr += "("
        elif key == ")":
            if self.expr.count("(") > self.expr.count(")") and self.expr[-1] not in OPERATORS + "(":
                self.expr += ")"
        self.refresh()

    def add_operator(self, key):
        if not self.expr:
            if key == "−":
                self.expr = "−"
            elif self.last_result:
                self.expr = self.last_result + key
            return
        if self.expr[-1] in OPERATORS:
            if key == "−" and self.expr[-1] in "×÷^":
                self.expr += key
            else:
                self.expr = self.expr[:-1] + key
        elif self.expr[-1] == "(":
            if key == "−":
                self.expr += key
        else:
            self.expr += key

    def calculate(self):
        if not self.expr:
            return
        expression = self.expr
        expression += ")" * (expression.count("(") - expression.count(")"))
        while expression and expression[-1] in OPERATORS:
            expression = expression[:-1]
        try:
            result = format_result(safe_eval(to_python(expression)))
        except ZeroDivisionError:
            self.show_error("Cannot divide by 0")
            return
        except Exception:
            self.show_error("Error")
            return
        self.history.text = expression + " ="
        self.last_result = result.replace("-", "−")
        self.expr = self.last_result
        self.refresh()

    def show_error(self, message):
        self.error = True
        self.history.text = self.expr
        self.display.text = message
        self.display.font_size = "32sp"


class CalculatorApp(App):
    def build(self):
        self.title = "Calculator"
        return Calculator()


if __name__ == "__main__":
    CalculatorApp().run()
