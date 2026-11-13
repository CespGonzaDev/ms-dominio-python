"""Helpers compartidos para cálculo y propagación de calificaciones de mentores."""

from app.repositories.protocols import ReviewRepository, ServiceRepository


def compute_rating_summary(reviews: list[dict]) -> dict:
    """Calcula promedio, conteo y distribución 1..5 a partir de reseñas visibles."""
    dist = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    total = 0
    count = 0
    for rev in reviews:
        if rev.get("hidden"):
            continue
        rating = int(rev.get("rating", 0))
        if 1 <= rating <= 5:
            dist[str(rating)] += 1
            total += rating
            count += 1
    avg = round(total / count, 1) if count else 0.0
    return {"average": avg, "count": count, "distribution": dist}


def recalculate_mentor_rating(
    mentor_id: str,
    review_repo: ReviewRepository,
    service_repo: ServiceRepository,
) -> dict:
    """Recalcula el promedio del mentor y lo sincroniza en todos sus servicios."""
    visible = review_repo.list_by_mentor(mentor_id, include_hidden=False)
    summary = compute_rating_summary(visible)
    _, services = service_repo.list_by_mentor(mentor_id)
    for doc in services:
        mentor = dict(doc.get("mentor") or {"id": mentor_id, "fullName": mentor_id})
        if (
            mentor.get("ratingAverage") != summary["average"]
            or mentor.get("ratingCount") != summary["count"]
        ):
            mentor["ratingAverage"] = summary["average"]
            mentor["ratingCount"] = summary["count"]
            doc["mentor"] = mentor
            service_repo.replace(doc)
    return summary
