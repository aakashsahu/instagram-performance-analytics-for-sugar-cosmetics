"""Sugar Cosmetics - Instagram Performance Analytics (Streamlit dashboard).

Run:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as A

st.set_page_config(page_title="Sugar Cosmetics | Instagram Analytics", page_icon="💄", layout="wide")

PINK, DARK, GOLD, TEAL, GREY = "#E6007E", "#1F2937", "#F5A623", "#14B8A6", "#9CA3AF"
PALETTE = [PINK, DARK, GOLD, TEAL, "#8B5CF6", "#EF4444"]
DATA_PATH = Path(__file__).parent / "sugar_cosmetics_instagram_clean.csv"

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem;}
      div[data-testid="stMetric"] {background:#fff7fb;border:1px solid #f6c9e0;border-radius:10px;padding:10px 14px;}
      .insight {background:#f8fafc;border-left:4px solid #E6007E;padding:10px 14px;margin:8px 0;border-radius:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading 50,000 posts...")
def get_data():
    return A.load_data(DATA_PATH)


def show(fig, height=380):
    """Render a Plotly figure (works across Streamlit versions)."""
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10),
                      font=dict(size=13), legend_title_text="")
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def table(d, **kw):
    d = d.copy()
    num = d.select_dtypes("number").columns
    d[num] = d[num].round(2)
    if "post_date" in d.columns:
        d["post_date"] = d["post_date"].dt.strftime("%Y-%m-%d")
    try:
        st.dataframe(d, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(d, use_container_width=True, hide_index=True, **kw)


def fmt(n):
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.2f}{unit}"
    return f"{n:,.0f}"


def verdict(df, by, label):
    """Plain-English read of whether a grouping really changes engagement."""
    s = A.group_summary(df, by)
    if len(s) < 2:
        return
    p = A.anova_p(df, by)
    best, worst = s.loc[s.avg_er.idxmax()], s.loc[s.avg_er.idxmin()]
    gap = best.avg_er - worst.avg_er
    if p < 0.05:
        msg = (f"**{label}:** {best[by]} leads ({best.avg_er:.2f}%) vs {worst[by]} ({worst.avg_er:.2f}%) "
               f"- a {gap:.2f} pt gap that is statistically significant (ANOVA p={p:.3f}).")
    else:
        msg = (f"**{label}:** the gap between best ({best[by]}, {best.avg_er:.2f}%) and worst ({worst[by]}, "
               f"{worst.avg_er:.2f}%) is only {gap:.2f} pts and **not statistically significant** (p={p:.2f}) - "
               f"treat the options as performing equally.")
    st.markdown(f'<div class="insight">{msg}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ data + filters
full = get_data()
st.sidebar.title("💄 Filters")
dmin, dmax = full.post_date.min().date(), full.post_date.max().date()
dates = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
types = st.sidebar.multiselect("Post type", sorted(full.post_type.unique()), default=sorted(full.post_type.unique()))
camps = st.sidebar.multiselect("Campaign type", sorted(full.campaign_type.unique()), default=sorted(full.campaign_type.unique()))
srcs = st.sidebar.multiselect("Engagement source", sorted(full.engagement_source.unique()), default=sorted(full.engagement_source.unique()))
emos = st.sidebar.multiselect("Audience emotion", sorted(full.audience_emotion.unique()), default=sorted(full.audience_emotion.unique()))
all_tags = sorted({t for s in full.hashtags.unique() for t in s.split("|")})
tags = st.sidebar.multiselect("Hashtag (post uses ANY selected)", all_tags, default=[])

df = full.copy()
if isinstance(dates, (tuple, list)) and len(dates) == 2:
    df = df[(df.post_date.dt.date >= dates[0]) & (df.post_date.dt.date <= dates[1])]
df = df[df.post_type.isin(types) & df.campaign_type.isin(camps) & df.engagement_source.isin(srcs) & df.audience_emotion.isin(emos)]
if tags:
    df = df[df.hashtags.apply(lambda s: any(t in s.split("|") for t in tags))]

st.sidebar.markdown("---")
st.sidebar.caption(f"{len(df):,} of {len(full):,} posts selected")
st.sidebar.caption("Engagement rate = (likes + comments + shares + saves) / reach")

st.title("Instagram Performance Analytics - Sugar Cosmetics")
st.caption("Apr 2024 - Apr 2025 | Interactive dashboard for the social media & marketing team")

if df.empty:
    st.warning("No posts match the current filters. Widen the filters in the sidebar.")
    st.stop()

tabs = st.tabs(["1 KPI Overview", "2 Posting Trend", "3-4 Top Posts", "5 Post Types & Campaigns",
                "6 Day of Week", "7 Engagement Funnel", "8 Hashtags", "Audience & Growth",
                "Strategy & Insights", "Data"])

# ------------------------------------------------------------------ 1 KPI
with tabs[0]:
    k = A.kpis(df)
    st.subheader("How is the account performing overall?")
    c = st.columns(5)
    c[0].metric("Total posts", f"{k['posts']:,}")
    c[1].metric("Total likes", fmt(k["likes"]))
    c[2].metric("Total comments", fmt(k["comments"]))
    c[3].metric("Total reach", fmt(k["reach"]))
    c[4].metric("Avg engagement rate", f"{k['avg_er']:.2f}%")
    c = st.columns(5)
    c[0].metric("Total shares", fmt(k["shares"]))
    c[1].metric("Total saves", fmt(k["saves"]))
    c[2].metric("Impressions", fmt(k["impressions"]))
    c[3].metric("Profile visits", fmt(k["profile_visits"]))
    c[4].metric("New follows", fmt(k["follows"]))
    c = st.columns(3)
    c[0].metric("Avg frequency (impressions / reach)", f"{k['frequency']:.2f}x")
    c[1].metric("Profile visit -> follow", f"{k['visit_to_follow']:.1f}%")
    c[2].metric("Follows per 1,000 reach", f"{k['follows_per_1k_reach']:.2f}")
    left, right = st.columns(2)
    with left:
        fig = px.histogram(df, x="engagement_rate", nbins=40, color_discrete_sequence=[PINK],
                           title="Distribution of post engagement rates")
        fig.update_layout(xaxis_title="Engagement rate (%)", yaxis_title="Posts")
        fig.add_vline(x=k["avg_er"], line_dash="dash", line_color=DARK, annotation_text=f"avg {k['avg_er']:.1f}%")
        show(fig)
    with right:
        mix = pd.DataFrame({"Interaction": ["Likes", "Comments", "Shares", "Saves"],
                            "Count": [k["likes"], k["comments"], k["shares"], k["saves"]]})
        fig = px.pie(mix, names="Interaction", values="Count", hole=0.5, color_discrete_sequence=PALETTE,
                     title="Where engagement comes from")
        show(fig)

# ------------------------------------------------------------------ 2 Trend
with tabs[1]:
    st.subheader("Monthly posting trend")
    m = A.monthly(df)
    fig = px.line(m, x="month", y="posts", markers=True, color_discrete_sequence=[PINK], title="Posts per month")
    fig.update_layout(xaxis_title="", yaxis_title="Posts")
    show(fig)
    st.caption("Apr 2024 and Apr 2025 are partial months (data runs 19 Apr 2024 - 19 Apr 2025), so their low counts are not a real drop.")
    left, right = st.columns(2)
    with left:
        fig = px.line(m, x="month", y="avg_er", markers=True, color_discrete_sequence=[DARK], title="Average engagement rate by month")
        fig.update_layout(xaxis_title="", yaxis_title="Engagement rate (%)")
        show(fig)
    with right:
        fig = px.bar(m, x="month", y="avg_reach", color_discrete_sequence=[TEAL], title="Average reach per post by month")
        fig.update_layout(xaxis_title="", yaxis_title="Reach")
        show(fig)

# ------------------------------------------------------------------ 3-4 Top posts
with tabs[2]:
    df_ = df.assign(post_id=df.index + 1)
    df_["label"] = "#" + df_.post_id.astype(str) + " | " + df_.post_label
    cols = ["post_id", "post_date", "post_type", "campaign_type", "hashtags", "likes", "comments", "shares", "saves", "reach", "engagement_rate"]
    left, right = st.columns(2)
    with left:
        st.subheader("Top 10 posts by likes")
        t = df_.nlargest(10, "likes").sort_values("likes")
        fig = px.bar(t, x="likes", y="label", orientation="h", color="post_type", color_discrete_sequence=PALETTE)
        fig.update_layout(yaxis_title="", xaxis_title="Likes")
        show(fig, 460)
    with right:
        st.subheader("Top 10 posts by engagement rate")
        t2 = df_.nlargest(10, "engagement_rate").sort_values("engagement_rate")
        fig = px.bar(t2, x="engagement_rate", y="label", orientation="h", color="post_type", color_discrete_sequence=PALETTE)
        fig.update_layout(yaxis_title="", xaxis_title="Engagement rate (%)")
        show(fig, 460)
    st.markdown("**Hidden gems** - high engagement rate on modest reach (top engagement-rate posts below the median reach):")
    gems = df_[df_.reach < df_.reach.median()].nlargest(10, "engagement_rate")[cols]
    table(gems)
    with st.expander("Full tables: top 10 by likes / by engagement rate"):
        table(df_.nlargest(10, "likes")[cols])
        table(df_.nlargest(10, "engagement_rate")[cols])
    st.caption("The dataset has no caption column, so posts are identified by ID, date, format and campaign.")

# ------------------------------------------------------------------ 5 Post type
with tabs[3]:
    st.subheader("Post type performance")
    s = A.group_summary(df, "post_type")
    long = s.melt(id_vars="post_type", value_vars=["avg_likes", "avg_comments", "avg_shares", "avg_saves"],
                  var_name="metric", value_name="avg")
    long["metric"] = long.metric.str.replace("avg_", "").str.title()
    left, right = st.columns(2)
    with left:
        fig = px.bar(long[long.metric == "Likes"], x="post_type", y="avg", color="post_type", color_discrete_sequence=PALETTE, title="Average likes per post")
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Likes")
        show(fig)
    with right:
        fig = px.bar(long[long.metric != "Likes"], x="post_type", y="avg", color="metric", barmode="group",
                     color_discrete_sequence=PALETTE, title="Average comments, shares and saves per post")
        fig.update_layout(xaxis_title="", yaxis_title="Average per post")
        show(fig)
    verdict(df, "post_type", "Post type")
    table(s)
    st.subheader("Campaign type")
    sc = A.group_summary(df, "campaign_type")
    fig = px.bar(sc.sort_values("avg_er"), x="avg_er", y="campaign_type", orientation="h", color_discrete_sequence=[PINK], title="Average engagement rate by campaign type")
    fig.update_layout(xaxis_title="Engagement rate (%)", yaxis_title="")
    show(fig, 320)
    verdict(df, "campaign_type", "Campaign type")
    st.subheader("Format x campaign heatmap (avg engagement rate %)")
    pv = df.pivot_table(index="post_type", columns="campaign_type", values="engagement_rate", aggfunc="mean")
    fig = px.imshow(pv.round(2), text_auto=".2f", color_continuous_scale="RdPu", aspect="auto")
    show(fig, 330)
    st.subheader("Engagement source")
    ss = A.group_summary(df, "engagement_source")
    fig = px.bar(ss, x="engagement_source", y="avg_er", color="engagement_source", color_discrete_sequence=PALETTE, title="Average engagement rate by source")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Engagement rate (%)")
    show(fig, 320)
    verdict(df, "engagement_source", "Engagement source")

# ------------------------------------------------------------------ 6 Day of week
with tabs[4]:
    st.subheader("Day-of-week analysis")
    d = A.group_summary(df, "weekday").sort_values("weekday")
    left, right = st.columns(2)
    with left:
        fig = px.bar(d, x="weekday", y="avg_er", color_discrete_sequence=[PINK], title="Average engagement rate by weekday")
        fig.update_layout(xaxis_title="", yaxis_title="Engagement rate (%)", yaxis_range=[0, max(25, d.avg_er.max() * 1.15)])
        show(fig)
    with right:
        fig = px.bar(d, x="weekday", y="posts", color_discrete_sequence=[DARK], title="Posts published by weekday")
        fig.update_layout(xaxis_title="", yaxis_title="Posts")
        show(fig)
    verdict(df, "weekday", "Day of week")
    hm = df.pivot_table(index="weekday", columns="month_label", values="engagement_rate", aggfunc="mean", observed=True)
    order = df.sort_values("month").month_label.unique()
    hm = hm[[c for c in order if c in hm.columns]]
    fig = px.imshow(hm.round(1), text_auto=".1f", color_continuous_scale="RdPu", aspect="auto", title="Engagement rate: weekday x month")
    show(fig, 400)
    st.caption("The dataset has date but no time-of-day, so intraday posting windows can't be assessed.")

# ------------------------------------------------------------------ 7 Funnel
with tabs[5]:
    st.subheader("Engagement funnel")
    f = A.funnel(df)
    fig = go.Figure(go.Funnel(y=f.stage, x=f.value, textinfo="value+percent initial",
                              marker=dict(color=[PINK, "#F472B6", DARK, TEAL, GOLD, "#8B5CF6"])))
    fig.update_layout(title="Impressions -> Reach -> Likes -> Comments -> Shares -> Saves")
    show(fig, 480)
    k = A.kpis(df)
    c = st.columns(5)
    c[0].metric("Reach / impressions", f"{k['reach'] / k['impressions'] * 100:.1f}%")
    c[1].metric("Likes / reach", f"{k['likes'] / k['reach'] * 100:.1f}%")
    c[2].metric("Comments / reach", f"{k['comments'] / k['reach'] * 100:.2f}%")
    c[3].metric("Shares / reach", f"{k['shares'] / k['reach'] * 100:.2f}%")
    c[4].metric("Saves / reach", f"{k['saves'] / k['reach'] * 100:.2f}%")
    st.markdown('<div class="insight">Likes, comments, shares and saves are actions on the same people, not a strict sequence - '
                'so the biggest "drop-off" is from reach to likes, and shares/saves (the high-intent actions) are under 1% of reach each.</div>',
                unsafe_allow_html=True)
    st.subheader("Funnel by post type (% of reach)")
    g = df.groupby("post_type", observed=True)[["reach", "likes", "comments", "shares", "saves"]].sum()
    pct = g.div(g["reach"], axis=0).drop(columns="reach").mul(100).reset_index().melt(id_vars="post_type", var_name="action", value_name="pct_of_reach")
    fig = px.bar(pct[pct.action != "likes"], x="post_type", y="pct_of_reach", color="action", barmode="group", color_discrete_sequence=PALETTE)
    fig.update_layout(xaxis_title="", yaxis_title="% of reach")
    show(fig, 340)

# ------------------------------------------------------------------ 8 Hashtags
with tabs[6]:
    st.subheader("Hashtag analysis")
    h = A.hashtag_summary(df)
    left, right = st.columns(2)
    with left:
        fig = px.bar(h.sort_values("uses"), x="uses", y="hashtag", orientation="h", color_discrete_sequence=[DARK], title="Most-used hashtags")
        fig.update_layout(xaxis_title="Posts using hashtag", yaxis_title="")
        show(fig, 340)
    with right:
        fig = px.bar(h.sort_values("avg_er"), x="avg_er", y="hashtag", orientation="h", color_discrete_sequence=[PINK], title="Average engagement rate by hashtag")
        fig.update_layout(xaxis_title="Engagement rate (%)", yaxis_title="")
        show(fig, 340)
    left, right = st.columns(2)
    with left:
        fig = px.bar(h.sort_values("avg_reach"), x="avg_reach", y="hashtag", orientation="h", color_discrete_sequence=[TEAL], title="Average reach by hashtag")
        fig.update_layout(xaxis_title="Reach per post", yaxis_title="")
        show(fig, 340)
    with right:
        n = A.group_summary(df, "n_hashtags")
        fig = px.bar(n, x="n_hashtags", y="avg_er", color_discrete_sequence=[GOLD], title="Average engagement rate by number of hashtags")
        fig.update_layout(xaxis_title="Hashtags per post", yaxis_title="Engagement rate (%)", xaxis=dict(dtick=1))
        show(fig, 340)
    verdict(df, "n_hashtags", "Hashtag count")
    st.markdown('<div class="insight">Only 5 distinct hashtags are used, each on roughly 40% of posts, and all deliver near-identical results. '
                'Hashtag choice is not currently a performance lever - the opportunity is to <b>test new/niche tags</b> to find one.</div>', unsafe_allow_html=True)
    table(h)

# ------------------------------------------------------------------ Audience & growth
with tabs[7]:
    st.subheader("Audience response and growth")
    m = A.monthly(df)
    left, right = st.columns(2)
    with left:
        fig = px.bar(m, x="month", y="follows", color_discrete_sequence=[PINK], title="New follows by month (volume)")
        fig.update_layout(xaxis_title="", yaxis_title="Follows")
        show(fig)
    with right:
        fig = px.line(m, x="month", y="follows_per_1k_reach", markers=True, color_discrete_sequence=[DARK], title="Follows per 1,000 reach (efficiency)")
        fig.update_layout(xaxis_title="", yaxis_title="Follows / 1K reach", yaxis_range=[0, max(12, m.follows_per_1k_reach.max() * 1.2)])
        show(fig)
    left, right = st.columns(2)
    with left:
        e = A.group_summary(df, "audience_emotion")
        fig = px.bar(e.sort_values("avg_er"), x="avg_er", y="audience_emotion", orientation="h", color_discrete_sequence=[TEAL], title="Engagement rate by audience emotion")
        fig.update_layout(xaxis_title="Engagement rate (%)", yaxis_title="")
        show(fig, 340)
        verdict(df, "audience_emotion", "Audience emotion")
    with right:
        fig = px.scatter(df.sample(min(len(df), 4000), random_state=1), x="reach", y="follows", color="post_type",
                         opacity=0.5, color_discrete_sequence=PALETTE, title="Reach vs follows (sample of 4,000 posts)")
        fig.update_layout(xaxis_title="Reach", yaxis_title="Follows")
        show(fig, 340)
    st.markdown('<div class="insight">Follower growth is <b>reach-driven</b>: roughly 9 follows per 1,000 people reached and ~30% of profile visits convert, '
                'consistently across every format, campaign and month. Growth = reach x constant conversion, so the lever is reaching more new people.</div>',
                unsafe_allow_html=True)

# ------------------------------------------------------------------ Strategy
with tabs[8]:
    st.subheader("Key takeaways (live - recalculated for the current filters)")
    k = A.kpis(df)
    st.markdown(f"- The selection has **{k['posts']:,} posts**, **{fmt(k['reach'])} reach** and a **{k['avg_er']:.2f}% average engagement rate**.")
    for by, lab in [("post_type", "Post type"), ("campaign_type", "Campaign type"), ("weekday", "Day of week"),
                    ("engagement_source", "Engagement source"), ("n_hashtags", "Hashtag count")]:
        verdict(df, by, lab)
    like_share = k["likes"] / (k["likes"] + k["comments"] + k["shares"] + k["saves"]) * 100
    st.markdown(f"- Likes make up **{like_share:.0f}%** of all interactions; comments, shares and saves together are the remaining {100 - like_share:.0f}%.")
    corr = df[["engagement_rate", "reach"]].corr().iloc[0, 1]
    st.markdown(f"- Correlation between reach and engagement rate: **{corr:.2f}** - bigger audiences do not dilute engagement, so scaling reach is safe.")
    st.subheader("Recommended strategy")
    st.markdown(
        """
1. **Stop optimising by format, weekday or hashtag - they're statistically equivalent.** Pick formats for production cost and brand fit (e.g. lean on Reels/Stories if cheaper) and spend the saved effort elsewhere.
2. **Focus on what moves engagement rate: like-rate per post.** Within every segment engagement ranges ~6% to ~34%. Run creative A/B tests (hook, product close-ups, UGC, shade swatches, creator faces) and codify what the top-decile posts share.
3. **Scale reach to scale followers.** ~9 follows per 1K reach and ~30% visit-to-follow are constants, so +10% reach ≈ +10% follows. Put incremental budget into reach (Reels discovery, collabs, paid boosts) rather than conversion tweaks.
4. **Fix the weak spot - shares and saves.** Each is <1% of reach. Create more save-worthy content (tutorial carousels, shade guides, "how to" checklists, dupes lists) and share-triggers (giveaway tag-a-friend, challenges).
5. **Test new hashtags.** All five tags perform identically; add niche (#ShadeMatch, #BudgetBeauty) and branded campaign tags and measure vs control. 2 tags marginally outperforms 1 (borderline significance).
6. **Add missing data.** Capture post time, captions, true carousel format, follower count and video views so future analysis can answer timing and creative questions.
        """
    )
    st.subheader("Campaign ideas")
    st.markdown(
        "- **#SugarShadeSwap** - UGC challenge pairing a Giveaway mechanic with tutorials (drives shares + saves).\n"
        "- **\"60-second Look\" Tutorial Reels series** with creators (Influencer Collab x Tutorial), weekly cadence.\n"
        "- **Festive countdown** - save-the-date carousels/stories before key sale moments, with a 'save this for later' CTA.\n"
        "- **Vegan & cruelty-free proof series** - turns the brand-values hashtags into content, A/B tested against generic posts."
    )

# ------------------------------------------------------------------ Data
with tabs[9]:
    st.subheader("Filtered data")
    table(df.drop(columns=["post_label", "month_label"]).head(2000))
    st.download_button("Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "sugar_cosmetics_filtered.csv", "text/csv")
    st.caption("Showing first 2,000 rows; the download contains every filtered row.")
