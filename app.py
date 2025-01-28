import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, timedelta


st.set_page_config(layout="wide")

def load_data():
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def categorize_lot(lot_name):
    """
    Fonction qui catégorise un lot en fonction de mots-clés
    Retourne une liste de catégories auxquelles le lot appartient
    """
    lot_name = lot_name.lower()
    categories = []
    
    category_keywords = {
        'Viande': ['viande', 'bœuf', 'veau', 'porc', 'agneau', 'mouton'],
        'Volaille': ['volaille', 'poulet', 'dinde'],
        'Charcuterie': ['charcuterie'],
        'Produits Laitiers': ['lait', 'produits laitiers', 'ovoproduits'],
        'Fruits et Légumes': ['fruits', 'légumes', 'aromates'],
        'Surgelés': ['surgelé'],
        'BIO': ['bio'],
        'Épicerie': ['épicerie', 'féculents', 'pâtes', 'riz', 'condiments', 'épices'],
        'Poisson': ['poisson'],
        'Boissons': ['boisson'],
        'Desserts': ['dessert', 'pâtisserie', 'compote']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in lot_name for keyword in keywords):
            categories.append(category)
    
    return categories

def prepare_timeline_data(data):
    timeline_data = []
    today = pd.Timestamp.now()
    
    for item in data:
        try:
            start_date = pd.to_datetime(item['date_debut'])
            end_date = pd.to_datetime(item['date_fin'])
            
            if pd.isna(start_date) or pd.isna(end_date):
                continue
                
            days_left = (end_date - today).days
            status = "Terminé" if days_left < 0 else "En cours"
            
            titulaires = ", ".join(item['titulaire']) if isinstance(item['titulaire'], list) else str(item['titulaire'])
            departments = item['code_departement'] if isinstance(item['code_departement'], list) else [str(item['code_departement'])]
            
            # Traitement des lots
            lots = item.get('LOTS', [])
            all_categories = set()
            for lot in lots:
                all_categories.update(categorize_lot(lot))
            
            timeline_data.append(dict(
                Task=f"[{status}] " + (item['objet'][:80] + '...' if len(item['objet']) > 80 else item['objet']),
                Start=start_date,
                Finish=end_date,
                Resource=item['nomacheteur'],
                Department=", ".join(departments),
                Departments=departments,
                Titulaire=titulaires,
                Days_Left=days_left,
                Status=status,
                Lots=lots,
                Categories=list(all_categories),
                URL=item.get('url_avis', '')  # Ajout de l'URL
            ))
        except (TypeError, ValueError, KeyError) as e:
            st.warning(f"Erreur avec l'entrée: {item.get('idweb', 'ID inconnu')} - {str(e)}")
            continue
            
    return pd.DataFrame(timeline_data)

def create_timeline_figure(df):
    df_active = df[df['Status'] == "En cours"]
    df_finished = df[df['Status'] == "Terminé"]
    
    fig = px.timeline(
        df_active,
        x_start='Start',
        x_end='Finish',
        y='Task',
        color='Resource',
        hover_data=['Titulaire', 'Days_Left', 'Status']
    )
    
    if not df_finished.empty:
        fig.add_traces(
            px.timeline(
                df_finished,
                x_start='Start',
                x_end='Finish',
                y='Task',
                color_discrete_sequence=['lightgray'],
                hover_data=['Titulaire', 'Days_Left', 'Status']
            ).data
        )
    
    today = datetime.now()
    fig.add_vline(
        x=today.strftime('%Y-%m-%d'),
        line_dash="dash",
        line_color="red"
    )
    
    fig.add_annotation(
        x=today.strftime('%Y-%m-%d'),
        y=1.05,
        text="Aujourd'hui",
        showarrow=False,
        yref='paper'
    )
    
    fig.update_layout(
        height=800,
        xaxis_title="Date",
        yaxis_title="Appels d'Offre",
        showlegend=True,
        title={
            'text': "Timeline des Appels d'Offre",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    start_range = today - timedelta(days=30)
    end_range = today + timedelta(days=365)
    
    fig.update_xaxes(
        range=[start_range.strftime('%Y-%m-%d'), end_range.strftime('%Y-%m-%d')]
    )
    
    return fig

def main():
    st.title("📊 Suivi des Appels d'Offre")
    
    data = load_data()
    df = prepare_timeline_data(data)
    
    if df.empty:
        st.error("Aucune donnée valide n'a été trouvée.")
        return
    
    # Filtres
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        acheteurs = sorted(list(set(df['Resource'])))
        selected_acheteurs = st.multiselect(
            "🏢 Acheteurs",
            acheteurs,
            help="Sélectionnez un ou plusieurs acheteurs"
        )

    with col2:
        titulaires = sorted(list(set([t.strip() for titulaire in df['Titulaire'].str.split(',') for t in titulaire])))
        selected_titulaires = st.multiselect(
            "👥 Titulaires",
            titulaires,
            help="Sélectionnez un ou plusieurs titulaires"
        )
    
    with col3:
        all_departments = sorted(list(set([dept for deps in df['Departments'] for dept in deps])))
        selected_departments = st.multiselect(
            "🗺️ Départements",
            all_departments,
            help="Sélectionnez un ou plusieurs départements"
        )

    with col4:
        expiration_filter = st.selectbox(
            "⚠️ Filtrer par date de fin",
            ["Tous les AO", 
             "Se termine dans 3 mois", 
             "Se termine dans 6 mois", 
             "Se termine dans 1 an",
             "Se termine dans 1 an et demi",
             "Se termine dans 2 ans"]
        )
    
    with col5:
        status_filter = st.multiselect(
            "📊 Statut",
            ["En cours", "Terminé"],
            default=["En cours"],
            help="Filtrer par statut des AO"
        )
        
    with col6:
        all_categories = sorted(list(set([cat for cats in df['Categories'] for cat in cats])))
        selected_categories = st.multiselect(
            "📦 Catégories de Lots",
            all_categories,
            help="Sélectionnez une ou plusieurs catégories de lots"
        )
    
    # Application des filtres
    filtered_df = df.copy()
    
    if selected_acheteurs:
        filtered_df = filtered_df[filtered_df['Resource'].isin(selected_acheteurs)]
    
    if selected_titulaires:
        filtered_df = filtered_df[filtered_df['Titulaire'].apply(lambda x: any(t.strip() in selected_titulaires for t in x.split(',')))]
    
    if selected_departments:
        filtered_df = filtered_df[filtered_df['Departments'].apply(lambda x: any(dept in selected_departments for dept in x))]
    
    if expiration_filter != "Tous les AO":
        if "3 mois" in expiration_filter:
            filtered_df = filtered_df[filtered_df['Days_Left'] <= 90]
        elif "6 mois" in expiration_filter:
            filtered_df = filtered_df[filtered_df['Days_Left'] <= 180]
        elif "1 an" in expiration_filter:
            filtered_df = filtered_df[filtered_df['Days_Left'] <= 365]
        elif "1 an et demi" in expiration_filter:
            filtered_df = filtered_df[filtered_df['Days_Left'] <= 547]
        elif "2 ans" in expiration_filter:
            filtered_df = filtered_df[filtered_df['Days_Left'] <= 730]
    
    if status_filter:
        filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]
        
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Categories'].apply(lambda x: any(cat in selected_categories for cat in x))]
    
    if not filtered_df.empty:
        # Création d'un dictionnaire pour stocker les ancres des détails
        detail_anchors = {}
        for idx, row in filtered_df.iterrows():
            anchor_id = f"detail_{idx}"
            detail_anchors[row['Task']] = anchor_id

        # Création du graphique
        fig = create_timeline_figure(filtered_df)
        
        # Affichage du graphique
        st.plotly_chart(fig, use_container_width=True)
        
        
        # Statistiques
        st.subheader("📈 Statistiques")
        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
        
        with stats_col1:
            st.metric("Nombre total d'AO", len(filtered_df))
        with stats_col2:
            active_aos = len(filtered_df[filtered_df['Status'] == "En cours"])
            st.metric("AO en cours", active_aos)
        with stats_col3:
            expiring_soon = len(filtered_df[(filtered_df['Days_Left'] <= 90) & (filtered_df['Days_Left'] >= 0)])
            st.metric("Se terminent dans 3 mois", expiring_soon)
        with stats_col4:
            finished_aos = len(filtered_df[filtered_df['Status'] == "Terminé"])
            st.metric("AO terminés", finished_aos)
            
        # Affichage des détails
        st.header("Détails des Appels d'Offre")
        for idx, row in filtered_df.iterrows():
            # Création d'un identifiant unique pour chaque détail
            st.markdown(f"<div id='{detail_anchors[row['Task']]}'></div>", unsafe_allow_html=True)
            
            with st.expander(row['Task']):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Acheteur:** {row['Resource']}")
                    st.write(f"**Titulaire:** {row['Titulaire']}")
                    st.write(f"**Départements:** {row['Department']}")
                    if row['URL']:  # Ajout du lien
                        st.markdown(f"**[Lien vers l'avis complet]({row['URL']})**")
                with col2:
                    st.write(f"**Date début:** {row['Start'].strftime('%Y-%m-%d')}")
                    st.write(f"**Date fin:** {row['Finish'].strftime('%Y-%m-%d')}")
                    st.write(f"**Statut:** {row['Status']}")
                st.write("**Lots et Catégories:**")
                for lot in row['Lots']:
                    categories = categorize_lot(lot)
                    st.write(f"- {lot}")
                    if categories:
                        st.write(f"  *Catégories: {', '.join(categories)}*")

        # Ajout du JavaScript pour permettre la navigation
        st.markdown("""
        <script>
            function scrollToDetail(detailId) {
                const element = document.getElementById(detailId);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth' });
                }
            }
        </script>
        """, unsafe_allow_html=True)

    else:
        st.warning("Aucune donnée ne correspond aux filtres sélectionnés")

if __name__ == "__main__":
    main()