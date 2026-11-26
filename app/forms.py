from django import forms

from .models import Contato, Custo, Servico


class FormServico(forms.ModelForm):
    class Meta:
        model = Servico
        fields = (
            "nome", "descricao", "categoria", "preco_custo", "preco",
            "estoque", "estoque_minimo", "link_ml", "imagem", "ativo",
        )
        widgets = {"descricao": forms.Textarea(attrs={"rows": 4})}
        help_texts = {
            "preco_custo": "Quanto a Carvalhos paga por unidade.",
            "preco": "Quanto o cliente paga.",
            "estoque_minimo": "Abaixo disso o produto aparece como estoque baixo.",
            "link_ml": "Opcional. Cole o endereço do anúncio para exibir o botão Ver no Mercado Livre.",
        }

    def clean(self):
        dados = super().clean()
        custo, preco = dados.get("preco_custo"), dados.get("preco")
        if custo is not None and preco is not None and preco < custo:
            self.add_error("preco", "O preço de venda está abaixo do custo: a venda daria prejuízo.")
        return dados


class FormContato(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ("nome", "telefone", "email", "mensagem")
        widgets = {"mensagem": forms.Textarea(attrs={"rows": 6})}


class FormCusto(forms.ModelForm):
    class Meta:
        model = Custo
        fields = ("descricao", "tipo", "valor", "data")
        widgets = {"data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {
            "valor": "Fixo: valor por mês. Variável: valor por unidade vendida.",
        }


class FormIntegrante(forms.Form):
    nome = forms.CharField(label="Nome completo", max_length=120)
    cargo = forms.CharField(label="Cargo", max_length=120)
    biografia = forms.CharField(label="Biografia", widget=forms.Textarea(attrs={"rows": 4}), required=False)
    foto_url = forms.URLField(label="Foto (URL)", required=False,
                              help_text="Link de uma imagem pública. Opcional.")
