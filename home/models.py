from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page


# ---------------------------------------------------------------------------
# Blocs réutilisables
# ---------------------------------------------------------------------------
class DomaineBlock(blocks.StructBlock):
    """Une carte de la section « mes domaines d'expertise » (sans gif)."""

    titre_principal = blocks.CharBlock(max_length=10, label="Gros mot (ex. 3D)")
    suffixe = blocks.CharBlock(max_length=10, required=False, label="Petit mot (ex. LA)")
    sous_titre = blocks.CharBlock(max_length=40, label="Sous-titre (ex. lighting)")
    categorie = blocks.ChoiceBlock(
        choices=[
            ("", "Aucune"),
            ("3d", "3D"),
            ("2d", "2D / UI UX"),
            ("son", "Son"),
        ],
        required=False,
        label="Montrer les œuvres de cette catégorie",
    )
    lien = blocks.PageChooserBlock(
        required=False,
        label="Page liée (utilisée seulement si aucune catégorie n'est choisie)",
    )

    class Meta:
        icon = "pick"
        label = "Domaine d'expertise"


class ReseauBlock(blocks.StructBlock):
    """Une ligne de la liste de réseaux sur la page Contact."""

    nom = blocks.CharBlock(max_length=60, label="Nom affiché (ex. leo_quenoy)")
    url = blocks.URLBlock(required=False, label="Lien")
    icone = ImageChooserBlock(required=False, label="Icône")

    class Meta:
        icon = "link"
        label = "Réseau"


class EtapeBlock(blocks.StructBlock):
    """Une étape de la frise « Mon parcours »."""

    annee = blocks.CharBlock(max_length=9, label="Année de début (ex. 2016)")
    annee_fin = blocks.CharBlock(
        max_length=9, required=False,
        label="Année de fin (à remplir seulement sur la dernière étape)",
    )
    titre = blocks.CharBlock(max_length=80, label="Titre")
    description = blocks.TextBlock(required=False, label="Description")

    class Meta:
        icon = "date"
        label = "Étape"


# ---------------------------------------------------------------------------
# Accueil
# ---------------------------------------------------------------------------
class HomePage(Page):
    max_count = 1  # une seule page d'accueil
    subpage_types = [
        "home.OeuvresIndexPage",
        "home.ParcoursPage",
        "home.ContactPage", "home.MentionsLegalesPage",
    ]

    # --- Hero ---
    hero_nom = models.CharField("Nom", max_length=60, default="Leo Quenoy")
    hero_titre = models.TextField(
        "Titre (un mot par ligne)", default="OCK\nTAN\nSTUDIO"
    )
    hero_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Logo (dans le rond)",
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Image du panneau de droite",
    )
    hero_cv = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="CV à télécharger",
    )
    page_parcours = models.ForeignKey(
        "wagtailcore.Page",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Page « Mon parcours »",
    )
    page_contact = models.ForeignKey(
        "wagtailcore.Page",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Page « Contact »",
    )

    # --- Domaines d'expertise (cartes) ---
    domaines = StreamField(
        [("domaine", DomaineBlock())],
        blank=True,
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("hero_nom"),
        FieldPanel("hero_titre"),
        FieldPanel("hero_logo"),
        FieldPanel("hero_image"),
        FieldPanel("hero_cv"),
        FieldPanel("page_parcours"),
        FieldPanel("page_contact"),
        FieldPanel("domaines"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["oeuvres_index"] = OeuvresIndexPage.objects.live().first()
        return context


# ---------------------------------------------------------------------------
# Mes œuvres
# ---------------------------------------------------------------------------
class OeuvresIndexPage(Page):
    """Page « Mes œuvres » : trois mosaïques (3D, 2D, son) séparées par des ★★."""

    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = ["home.OeuvrePage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # L'ordre des tuiles = l'ordre des pages dans l'explorateur Wagtail
        oeuvres = list(
            OeuvrePage.objects.child_of(self).live()
            .select_related("image")
            .order_by("path")
        )
        sections = []
        for code, _label in OeuvrePage.CATEGORIES:
            items = [o for o in oeuvres if o.categorie == code]
            if items:
                sections.append(
                    {
                        "code": code,
                        "label": OeuvrePage.LABELS_MOSAIQUE[code],
                        "oeuvres": items,
                    }
                )
        # ?categorie=3d / 2d / son : n'affiche que cette mosaïque
        code = request.GET.get("categorie")
        if code in OeuvrePage.LABELS_MOSAIQUE:
            sections = [s for s in sections if s["code"] == code]
            context["categorie_active"] = code
        context["sections"] = sections
        return context


class OeuvrePage(Page):
    parent_page_types = ["home.OeuvresIndexPage"]
    subpage_types = []

    CATEGORIES = [("3d", "3D"), ("2d", "2D / UI UX"), ("son", "Son")]
    LABELS_MOSAIQUE = {"3d": "3D", "2d": "2D", "son": "son"}

    TAILLES = [
        ("petite", "Petite (1 × 1)"),
        ("haute", "Haute (1 × 2)"),
        ("tres_haute", "Très haute (1 × 3)"),
        ("large", "Large (3 × 1)"),
        ("grande", "Grande (2 × 2)"),
    ]

    categorie = models.CharField(max_length=10, choices=CATEGORIES, default="3d")
    taille = models.CharField(
        "Taille de la tuile dans la mosaïque",
        max_length=12, choices=TAILLES, default="petite",
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    fichier_audio = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Fichier audio (catégorie Son)",
    )
    description = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("categorie"),
        FieldPanel("taille"),
        FieldPanel("image"),
        FieldPanel("fichier_audio"),
        FieldPanel("description"),
    ]

    @property
    def classe_taille(self):
        return "tuile--" + self.taille.replace("_", "-")


# ---------------------------------------------------------------------------
# Mon parcours
# ---------------------------------------------------------------------------
class ParcoursPage(Page):
    """Frise chronologique : les lignes s'assombrissent de la plus ancienne à la plus récente."""

    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = []

    etapes = StreamField(
        [("etape", EtapeBlock())],
        blank=True,
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("etapes"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        blocs = list(self.etapes)
        total = len(blocs)
        context["etapes"] = [
            {
                "annee": b.value["annee"],
                "fin": b.value["annee_fin"],
                "titre": b.value["titre"],
                "description": b.value["description"],
                # 0 (clair) -> 100 (sombre), entier pour éviter la virgule locale
                "pct": round(100 * i / (total - 1)) if total > 1 else 0,
            }
            for i, b in enumerate(blocs)
        ]
        return context


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class ContactPage(Page):
    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = []

    email = models.EmailField("E-mail", blank=True)
    telephone = models.CharField("Téléphone", max_length=20, blank=True)
    cv = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="CV à télécharger",
    )
    reseaux = StreamField(
        [("reseau", ReseauBlock())],
        blank=True,
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("email"),
        FieldPanel("telephone"),
        FieldPanel("cv"),
        FieldPanel("reseaux"),
    ]


# ---------------------------------------------------------------------------
# Mentions légales
# ---------------------------------------------------------------------------
MENTIONS_PAR_DEFAUT = """
<h2>Éditeur du site</h2>
<p>Ce site est édité par Leo Quenoy, illustrateur 2D/3D et UI/UX, sous le nom Studio Ocktan.</p>
<p>Statut : [À COMPLÉTER : particulier, auto-entrepreneur, société…]</p>
<p>Adresse : [À COMPLÉTER]</p>
<p>E-mail : [À COMPLÉTER]</p>
<p>Téléphone : [À COMPLÉTER]</p>
<p>N° SIRET (si vous en avez un) : [À COMPLÉTER]</p>
<p>Directeur de la publication : Leo Quenoy.</p>

<h2>Hébergement</h2>
<p>Le site est hébergé par : [À COMPLÉTER : nom de l'hébergeur, adresse, site web et téléphone].</p>

<h2>Propriété intellectuelle</h2>
<p>Les illustrations, modèles 3D, créations sonores, textes et mises en page présents sur ce site sont des œuvres de Leo Quenoy, sauf mention contraire. Toute reproduction, représentation ou réutilisation, même partielle, est interdite sans autorisation écrite préalable.</p>

<h2>Données personnelles</h2>
<p>Ce site ne comporte pas de formulaire et ne dépose pas de cookies publicitaires ni de suivi. Si vous m'écrivez par e-mail, vos données (adresse e-mail, contenu du message) ne servent qu'à vous répondre et ne sont pas transmises à des tiers.</p>
<p>Les polices de caractères du site sont chargées depuis le service Google Fonts : votre adresse IP est alors transmise à Google. [À ADAPTER : supprimez cette phrase si vous hébergez les polices vous-même.]</p>
<p>Conformément au règlement général sur la protection des données (RGPD) et à la loi Informatique et Libertés, vous disposez d'un droit d'accès, de rectification et d'effacement de vos données. Pour l'exercer, écrivez à l'adresse e-mail indiquée plus haut. Vous pouvez aussi adresser une réclamation à la CNIL (www.cnil.fr).</p>

<h2>Liens externes</h2>
<p>Ce site contient des liens vers d'autres sites (réseaux sociaux, portfolios). Leo Quenoy n'est pas responsable de leur contenu.</p>

<h2>Crédits</h2>
<p>Conception, illustrations et développement : Leo Quenoy. Site réalisé avec Wagtail (Django).</p>
"""


class MentionsLegalesPage(Page):
    """Page « Mentions légales » : texte modifiable dans l'admin."""

    max_count = 1
    parent_page_types = ["home.HomePage"]
    subpage_types = []

    contenu = RichTextField(
        "Texte",
        default=MENTIONS_PAR_DEFAUT,
        features=["h2", "h3", "bold", "italic", "link", "ol", "ul"],
    )
    mise_a_jour = models.DateField("Dernière mise à jour", null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("contenu"),
        FieldPanel("mise_a_jour"),
    ]
