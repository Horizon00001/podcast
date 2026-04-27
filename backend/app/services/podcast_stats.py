from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.models.podcast import Podcast


def update_podcast_completion_stats(db: Session, podcast_id: int) -> None:
    result = db.execute(
        select(
            func.avg(Interaction.progress_pct).label("rate"),
            func.count(Interaction.id).label("count"),
        ).where(
            Interaction.podcast_id == podcast_id,
            Interaction.progress_pct.isnot(None),
        )
    ).first()

    rate = float(result.rate) if result.rate is not None else None
    count = result.count if result.count else None

    db.execute(
        Podcast.__table__.update()
        .where(Podcast.id == podcast_id)
        .values(completion_rate=rate, completion_count=count)
    )
    db.commit()


def compute_all_podcast_stats(db: Session) -> None:
    result = db.execute(
        select(
            Interaction.podcast_id,
            func.avg(Interaction.progress_pct).label("rate"),
            func.count(Interaction.id).label("count"),
        )
        .where(Interaction.progress_pct.isnot(None))
        .group_by(Interaction.podcast_id)
    ).all()

    for row in result:
        db.execute(
            Podcast.__table__.update()
            .where(Podcast.id == row.podcast_id)
            .values(completion_rate=float(row.rate), completion_count=row.count)
        )

    db.commit()