class NewsPostService:
    def __init__(self, processed_repo, logger):
        self.repo = processed_repo
        self.logger = logger

    def get_post(self, post_id):
        return self.repo.fetch_by_id(post_id)

    def update_text(self, post_id, text):
        self.repo.update_text(post_id, text)
        self.logger.info(f"Text updated for post {post_id}")

    def update_url(self, post_id, url):
        self.repo.update_url(post_id, url)
        self.logger.info(f"URL updated for post {post_id}")

    def update_media(self, post_id, media_ids):
        self.repo.update_media(post_id, media_ids)
        self.logger.info(f"Media updated for post {post_id}")

    def mark_confirmed(self, post_id):
        self.repo.mark_confirmed([post_id])
        self.logger.info(f"Post {post_id} confirmed")

    def mark_rejected(self, post_id):
        self.repo.mark_rejected([post_id])
        self.logger.info(f"Post {post_id} rejected")
