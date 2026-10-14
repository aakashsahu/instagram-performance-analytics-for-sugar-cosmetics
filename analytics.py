"""Shared data + metric helpers for the Sugar Cosmetics Instagram dashboard."""
import numpy as np
import pandas as pd

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
INTERACTIONS = ["likes", "comments", "shares", "saves"]


def load_data(path="sugar_cosmetics_instagram_clean.csv"):
    df = pd.read_csv(path, parse_dates=["post_date"])
    df["interactions"] = df[INTERACTIONS].sum(axis=1)
    df["engagement_rate"] = df["interactions"] / df["reach"] * 100
    df["weekday"] = pd.Categorical(df["post_date"].dt.day_name(), categories=DAYS, ordered=True)
    df["month"] = df["post_date"].dt.to_period("M").dt.to_timestamp()
    df["month_label"] = df["month"].dt.strftime("%b %Y")
    df["n_hashtags"] = df["hashtags"].str.count(r"\|") + 1
    df["like_rate"] = df["likes"] / df["reach"] * 100
    df["follows_per_1k_reach"] = df["follows"] / df["reach"] * 1000
    df["post_label"] = (
        df["post_date"].dt.strftime("%d %b %Y") + " | " + df["post_type"] + " | " + df["campaign_type"]
    )
    return df


def kpis(df):
    reach = df["reach"].sum()
    return {
        "posts": len(df),
        "likes": int(df["likes"].sum()),
        "comments": int(df["comments"].sum()),
        "shares": int(df["shares"].sum()),
        "saves": int(df["saves"].sum()),
        "reach": int(reach),
        "impressions": int(df["impressions"].sum()),
        "profile_visits": int(df["profile_visits"].sum()),
        "follows": int(df["follows"].sum()),
        "avg_er": float(df["engagement_rate"].mean()) if len(df) else 0.0,
        "weighted_er": float(df["interactions"].sum() / reach * 100) if reach else 0.0,
        "frequency": float(df["impressions"].sum() / reach) if reach else 0.0,
        "visit_to_follow": float(df["follows"].sum() / df["profile_visits"].sum() * 100) if len(df) else 0.0,
        "follows_per_1k_reach": float(df["follows"].sum() / reach * 1000) if reach else 0.0,
    }


def group_summary(df, by):
    g = df.groupby(by, observed=True)
    out = g.agg(
        posts=("engagement_rate", "size"),
        avg_er=("engagement_rate", "mean"),
        avg_likes=("likes", "mean"),
        avg_comments=("comments", "mean"),
        avg_shares=("shares", "mean"),
        avg_saves=("saves", "mean"),
        avg_reach=("reach", "mean"),
        follows=("follows", "sum"),
        reach=("reach", "sum"),
        profile_visits=("profile_visits", "sum"),
    ).reset_index()
    out["follows_per_1k_reach"] = out["follows"] / out["reach"] * 1000
    out["visit_to_follow"] = out["follows"] / out["profile_visits"] * 100
    return out


def monthly(df):
    m = group_summary(df, "month").sort_values("month")
    m["month_label"] = m["month"].dt.strftime("%b %Y")
    return m


def hashtag_summary(df):
    ex = df.assign(hashtag=df["hashtags"].str.split("|")).explode("hashtag")
    h = ex.groupby("hashtag").agg(
        uses=("engagement_rate", "size"),
        avg_er=("engagement_rate", "mean"),
        avg_reach=("reach", "mean"),
        avg_likes=("likes", "mean"),
        follows=("follows", "sum"),
        reach=("reach", "sum"),
    ).reset_index()
    h["follows_per_1k_reach"] = h["follows"] / h["reach"] * 1000
    return h.sort_values("uses", ascending=False)


def funnel(df):
    return pd.DataFrame(
        {
            "stage": ["Impressions", "Reach", "Likes", "Comments", "Shares", "Saves"],
            "value": [df["impressions"].sum(), df["reach"].sum(), df["likes"].sum(),
                      df["comments"].sum(), df["shares"].sum(), df["saves"].sum()],
        }
    )


def anova_p(df, by):
    """One-way ANOVA p-value of engagement rate across groups (small p = real difference)."""
    from scipy import stats
    groups = [g["engagement_rate"].values for _, g in df.groupby(by, observed=True) if len(g) > 1]
    if len(groups) < 2:
        return float("nan")
    return float(stats.f_oneway(*groups).pvalue)
