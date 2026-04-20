import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client
import time
import base64
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="iSTEP Exercise Tracker",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.timer-display {
    font-size: 2.4rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.05em;
    text-align: center;
    padding: 12px 0 4px;
}
.activity-card {
    background: var(--secondary-background-color);
    border-radius: 12px;
    padding: 20px 16px 16px;
    margin-bottom: 8px;
    text-align: center;
}
.activity-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 4px;
}
.activity-header img   { height: 2rem; width: auto; }
.activity-header .act-emoji { font-size: 2rem; line-height: 1; }
.activity-header .act-name  { font-size: 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Participant ID from URL ───────────────────────────────────────────────────
params = st.query_params
subject_id = params.get("id", None)

if not subject_id:
    st.error("⚠️ No participant ID found in the URL. Please use your personal study link.")
    st.info("Your link should look like: `https://your-app.streamlit.app?id=P001`")
    st.stop()

# ── Supabase connection ───────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

def load_activities(pid: str) -> pd.DataFrame:
    sb = get_supabase()
    res = sb.table("activities").select("*").eq("subject_id", pid).execute()
    if not res.data:
        return pd.DataFrame(columns=[
            "subject_id", "date", "activity_type", "duration_minutes", "timestamp"
        ])
    return pd.DataFrame(res.data)

def load_goals(pid: str) -> pd.DataFrame:
    sb = get_supabase()
    res = sb.table("goals").select("*").eq("subject_id", pid).execute()
    if not res.data:
        return pd.DataFrame(columns=[
            "subject_id", "week_number", "week_start",
            "strength_goal", "aerobic_goal"
        ])
    return pd.DataFrame(res.data)

def save_activity(pid: str, activity_type: str, duration_minutes: float,
                  used_resource: str, synchrony: str):
    sb = get_supabase()
    sb.table("activities").insert({
        "subject_id":       pid,
        "date":             date.today().isoformat(),
        "activity_type":    activity_type,
        "duration_minutes": round(duration_minutes, 2),
        "timestamp":        datetime.now().isoformat(),
        "used_resource":    used_resource,
        "synchrony":        synchrony
    }).execute()

def save_goal(pid: str, week_number: int, week_start: str,
              strength_goal: int, aerobic_goal: int):
    sb = get_supabase()
    sb.table("goals").upsert({
        "subject_id": pid,
        "week_number":    week_number,
        "week_start":     week_start,
        "strength_goal":  strength_goal,
        "aerobic_goal":   aerobic_goal,
    }, on_conflict="subject_id,week_number").execute()

# ── Image helper ─────────────────────────────────────────────────────────────
def img_to_html(path: str, height: str = "2rem") -> str:
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
        return f'<img src="data:{mime};base64,{b64}" style="height:{height};width:auto;">'
    except Exception:
        return ""

# ── Study configuration ───────────────────────────────────────────────────────
# !! Update STUDY_START to your actual study start date !!
STUDY_START = date(2026, 5, 1)
STUDY_WEEKS = 32  # ~8 months
today           = date.today()
current_week    = max(1, min(STUDY_WEEKS, ((today - STUDY_START).days // 7) + 1))
week_start_date = STUDY_START + timedelta(weeks=current_week - 1)
week_end_date   = week_start_date + timedelta(days=6)

# ── Activity definitions ──────────────────────────────────────────────────────
ACTIVITIES = [
    {"name": "Strength Training", "icon": "🏋️", "img": None,              "color": "#7F77DD", "key": "strength",     "resource_label": "Did you use the iSTEP video tutorial?"},
    {"name": "Aerobic Steps",     "icon": "🏃", "img": "image-steps.png", "color": "#1D9E75", "key": "aero_steps",   "resource_label": "Did you use the iSTEP audio playlist?"},
    {"name": "Walk & Jog",        "icon": "🚶", "img": "image-jog.png",   "color": "#EF9F27", "key": "walk_jog",     "resource_label": "Did you use the iSTEP audio playlist?"},
    {"name": "Other Aerobic",     "icon": "🤸", "img": None,              "color": "#D85A30", "key": "other_aerobic","resource_label": "Did you use the iSTEP audio playlist?"},
]

# ── Session state init ────────────────────────────────────────────────────────
for act in ACTIVITIES:
    k = act["key"]
    st.session_state.setdefault(f"running_{k}",      False)
    st.session_state.setdefault(f"start_time_{k}",   None)
    st.session_state.setdefault(f"elapsed_{k}",      0.0)
    st.session_state.setdefault(f"saved_{k}",        False)
    st.session_state.setdefault(f"used_resource_{k}", "Yes")
    st.session_state.setdefault(f"synchrony_{k}",    "Moderately")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.6rem; white-space:nowrap; margin-bottom:4px;'>"
    "iSTEP Exercise Tracker</h1>",
    unsafe_allow_html=True
)
st.markdown(
    f"<p style='font-size:0.85rem; margin-top:0; white-space:nowrap; "
    f"overflow:hidden; text-overflow:ellipsis;'>"
    f"Participant &nbsp;<strong>{subject_id}</strong>"
    f"&nbsp;·&nbsp;"
    f"Week <strong>{current_week}</strong> of {STUDY_WEEKS}"
    f"&nbsp;·&nbsp;"
    f"<strong>{today.strftime('%A, %B %d, %Y')}</strong>"
    f"</p>",
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["📅 Log Activity", "🎯 Weekly Goals", "📈 My Progress"])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOG ACTIVITY
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Today's Activities")

    any_running = any(st.session_state[f"running_{a['key']}"] for a in ACTIVITIES)

    cols = st.columns(4)
    for i, act in enumerate(ACTIVITIES):
        k = act["key"]
        with cols[i]:
            running = st.session_state[f"running_{k}"]
            elapsed = st.session_state[f"elapsed_{k}"]
            saved   = st.session_state[f"saved_{k}"]

            if running and st.session_state[f"start_time_{k}"]:
                display_secs = time.time() - st.session_state[f"start_time_{k}"]
            else:
                display_secs = elapsed * 60

            mins_d = int(display_secs // 60)
            secs_d = int(display_secs % 60)

            st.markdown("<div class='activity-card'>", unsafe_allow_html=True)

            # Icon and name on one line
            if act.get("img"):
                icon_html = img_to_html(act["img"], height="2rem")
            else:
                icon_html = f'<span class="act-emoji">{act["icon"]}</span>'
            st.markdown(
                f"<div class='activity-header'>"
                f"{icon_html}"
                f"<span class='act-name'>{act['name']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            if saved:
                st.markdown(
                    f"<div class='timer-display' style='color:{act['color']}'>✓ Saved</div>",
                    unsafe_allow_html=True
                )
                if st.button("Log another", key=f"reset_{k}", use_container_width=True):
                    st.session_state[f"saved_{k}"]   = False
                    st.session_state[f"elapsed_{k}"] = 0.0
                    st.rerun()
            else:
                color = act["color"] if running else "inherit"
                st.markdown(
                    f"<div class='timer-display' style='color:{color}'>"
                    f"{mins_d:02d}:{secs_d:02d}</div>",
                    unsafe_allow_html=True
                )

                if running:
                    if st.button("⏹ Stop", key=f"stop_{k}",
                                 use_container_width=True, type="primary"):
                        total_secs = time.time() - st.session_state[f"start_time_{k}"]
                        st.session_state[f"elapsed_{k}"]    = total_secs / 60
                        st.session_state[f"running_{k}"]    = False
                        st.session_state[f"start_time_{k}"] = None
                        st.rerun()
                else:
                    if elapsed > 0:
                        # ── Follow-up questions (shown after stopping) ──
                        used_resource = st.radio(
                            act["resource_label"],
                            ["Yes", "No"],
                            key=f"used_resource_{k}",
                            horizontal=True
                        )
                        if used_resource == "Yes":
                            synchrony = st.selectbox(
                                "Synchrony between exercise tempo and auditory cues:",
                                ["Not at all", "Slightly", "Moderately",
                                 "Mostly", "Completely"],
                                key=f"synchrony_{k}"
                            )
                        else:
                            synchrony = "N/A"
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("▶ Resume", key=f"resume_{k}",
                                         use_container_width=True):
                                st.session_state[f"running_{k}"]    = True
                                st.session_state[f"start_time_{k}"] = (
                                    time.time() - (elapsed * 60)
                                )
                                st.rerun()
                        with c2:
                            if st.button("💾 Save", key=f"save_{k}",
                                         use_container_width=True, type="primary"):
                                try:
                                    save_activity(
                                        subject_id, act["name"], elapsed,
                                        used_resource, synchrony
                                    )
                                    st.session_state[f"saved_{k}"]   = True
                                    st.session_state[f"elapsed_{k}"] = 0.0
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Could not save: {e}")
                        if st.button("✕ Discard", key=f"discard_{k}",
                                     use_container_width=True):
                            st.session_state[f"elapsed_{k}"] = 0.0
                            st.rerun()
                    else:
                        if st.button("▶ Start", key=f"start_{k}",
                                     use_container_width=True, type="primary"):
                            st.session_state[f"running_{k}"]    = True
                            st.session_state[f"start_time_{k}"] = time.time()
                            st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    if any_running:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=1000, key="live_timer")
        except ImportError:
            st.caption("⚠️ Install `streamlit-autorefresh` for a live timer display.")

    st.divider()
    st.subheader("Today's Log")
    try:
        df_today = load_activities(subject_id)
        if not df_today.empty:
            today_rows = df_today[df_today["date"] == today.isoformat()].copy()
            if not today_rows.empty:
                today_rows["duration_minutes"] = pd.to_numeric(today_rows["duration_minutes"])
                display = today_rows[["activity_type", "duration_minutes"]].rename(
                    columns={"activity_type": "Activity", "duration_minutes": "Duration (min)"}
                )
                st.dataframe(display, use_container_width=True, hide_index=True)
                st.caption(
                    f"Total today: **{today_rows['duration_minutes'].sum():.1f} min**"
                )
            else:
                st.caption("No activities logged today yet.")
        else:
            st.caption("No activities logged today yet.")
    except Exception as e:
        st.warning(f"Could not load today's log: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — WEEKLY GOALS
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"Set Goals for Week {current_week}")
    st.caption(
        f"{week_start_date.strftime('%b %d')} – {week_end_date.strftime('%b %d, %Y')}"
    )

    try:
        df_goals = load_goals(subject_id)
        existing = pd.DataFrame()
        if not df_goals.empty:
            df_goals["week_number"] = pd.to_numeric(
                df_goals["week_number"], errors="coerce"
            )
            existing = df_goals[df_goals["week_number"] == current_week]
    except Exception:
        df_goals = pd.DataFrame()
        existing = pd.DataFrame()

    default_strength = int(existing["strength_goal"].values[0]) if not existing.empty else 30
    default_aerobic  = int(existing["aerobic_goal"].values[0])  if not existing.empty else 150

    with st.form("goal_form"):
        gc1, gc2 = st.columns(2)
        with gc1:
            st.markdown("**💪 Strength Training**")
            st.caption("Minutes per week")
            strength_goal = st.number_input(
                "Minutes/week", min_value=0, max_value=840,
                value=default_strength, step=5, label_visibility="collapsed"
            )
        with gc2:
            st.markdown("**🏃 Aerobic Training**")
            st.caption("Minutes per week")
            aerobic_goal = st.number_input(
                "Minutes/week", min_value=0, max_value=840,
                value=default_aerobic, step=5, label_visibility="collapsed"
            )
        if st.form_submit_button(
            "💾 Save Goals for This Week",
            use_container_width=True, type="primary"
        ):
            try:
                save_goal(
                    subject_id, current_week,
                    week_start_date.isoformat(),
                    int(strength_goal), int(aerobic_goal)
                )
                st.success(f"✅ Goals saved for Week {current_week}!")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save goals: {e}")

    st.divider()
    st.subheader("All Weekly Goals")
    try:
        df_goals_all = load_goals(subject_id)
        if not df_goals_all.empty:
            disp = df_goals_all[[
                "week_number", "week_start",
                "strength_goal", "aerobic_goal"
            ]].copy()
            disp.columns = [
                "Week", "Week Starting",
                "💪 Strength (min)", "🏃 Aerobic Training (min)",
            ]
            disp["Week"] = pd.to_numeric(disp["Week"])
            st.dataframe(
                disp.sort_values("Week"), use_container_width=True, hide_index=True
            )
        else:
            st.caption("No goals set yet. Use the form above to get started.")
    except Exception as e:
        st.warning(f"Could not load goals: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — PROGRESS CHART
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("My Progress — 8 Months")

    try:
        df_acts_prog  = load_activities(subject_id)
        df_goals_prog = load_goals(subject_id)

        if df_acts_prog.empty:
            st.info(
                "📭 No activity data yet. "
                "Start logging in **Log Activity** to see your progress here."
            )
        else:
            df_acts_prog["date"] = pd.to_datetime(df_acts_prog["date"])
            df_acts_prog["duration_minutes"] = pd.to_numeric(
                df_acts_prog["duration_minutes"], errors="coerce"
            )
            df_acts_prog["week_number"] = (
                (df_acts_prog["date"] - pd.Timestamp(STUDY_START)).dt.days // 7
            ) + 1

            # Combine all aerobic activities into a single "Aerobic Training" group
            AEROBIC_TYPES = {"Aerobic Steps", "Walk & Jog", "Other Aerobic"}
            df_acts_prog["chart_group"] = df_acts_prog["activity_type"].apply(
                lambda x: "Aerobic Training" if x in AEROBIC_TYPES else x
            )

            weekly_totals = (
                df_acts_prog
                .groupby(["week_number", "chart_group"])["duration_minutes"]
                .sum()
                .reset_index()
            )

            # Two chart lines: Strength Training + Aerobic Training
            CHART_LINES = [
                {"name": "Strength Training", "color": "#7F77DD"},
                {"name": "Aerobic Training",  "color": "#1D9E75"},
            ]

            fig = go.Figure()

            for line in CHART_LINES:
                line_data = weekly_totals[weekly_totals["chart_group"] == line["name"]]
                if not line_data.empty:
                    fig.add_trace(go.Scatter(
                        x=line_data["week_number"],
                        y=line_data["duration_minutes"],
                        name=line["name"],
                        mode="lines+markers",
                        line=dict(color=line["color"], width=2.5),
                        marker=dict(size=7, color=line["color"]),
                        hovertemplate=(
                            f"<b>{line['name']}</b><br>"
                            "Week %{x}<br>%{y:.0f} min<extra></extra>"
                        )
                    ))

            if not df_goals_prog.empty:
                df_goals_prog["week_number"] = pd.to_numeric(
                    df_goals_prog["week_number"], errors="coerce"
                )
                for col, act_name, color in [
                    ("strength_goal", "Strength Training", "#7F77DD"),
                    ("aerobic_goal",  "Aerobic Training",  "#1D9E75"),
                ]:
                    df_goals_prog[col] = pd.to_numeric(
                        df_goals_prog[col], errors="coerce"
                    )
                    fig.add_trace(go.Scatter(
                        x=df_goals_prog["week_number"],
                        y=df_goals_prog[col],
                        name=f"{act_name} goal",
                        mode="lines",
                        line=dict(color=color, width=1.5, dash="dash"),
                        opacity=0.45,
                        hovertemplate=(
                            f"<b>{act_name} goal</b><br>"
                            "Week %{x}<br>%{y:.0f} min<extra></extra>"
                        )
                    ))

            fig.add_vline(
                x=current_week,
                line_width=1.5, line_dash="dot",
                line_color="rgba(128,128,128,0.5)",
                annotation_text=f"Week {current_week}",
                annotation_position="top"
            )
            fig.update_layout(
                xaxis=dict(
                    title="Week",
                    range=[0.5, STUDY_WEEKS + 0.5],
                    tickmode="linear", tick0=1, dtick=4,
                    gridcolor="rgba(128,128,128,0.15)"
                ),
                yaxis=dict(
                    title="Minutes",
                    gridcolor="rgba(128,128,128,0.15)"
                ),
                legend=dict(
                    orientation="h", yanchor="bottom",
                    y=1.02, xanchor="left", x=0
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=60, b=40, l=40, r=20),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Solid lines = actual minutes logged · Dashed lines = weekly goals"
            )

            st.divider()
            st.subheader("Summary")
            sc1, sc2 = st.columns(2)

            # Strength Training
            with sc1:
                st_df  = df_acts_prog[df_acts_prog["activity_type"] == "Strength Training"]
                st_tot = st_df["duration_minutes"].sum()
                st_wks = st_df["week_number"].nunique()
                st.metric(
                    label="💪 Strength Training",
                    value=f"{st_tot:.0f} min total",
                    delta=f"{st_tot / max(st_wks, 1):.0f} min/week avg"
                )

            # Aerobic Training (Aerobic Steps + Walk & Jog combined)
            with sc2:
                ae_df  = df_acts_prog[df_acts_prog["activity_type"].isin(AEROBIC_TYPES)]
                ae_tot = ae_df["duration_minutes"].sum()
                ae_wks = ae_df["week_number"].nunique()
                st.metric(
                    label="🏃 Aerobic Training",
                    value=f"{ae_tot:.0f} min total",
                    delta=f"{ae_tot / max(ae_wks, 1):.0f} min/week avg"
                )

    except Exception as e:
        st.error(f"Could not load progress data: {e}")
