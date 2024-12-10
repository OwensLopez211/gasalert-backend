from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ReportLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="report_logs")
    report_type = models.CharField(max_length=50)  # PDF, Excel, CSV
    date_range = models.CharField(max_length=50)  # today, week, month, etc.
    generated_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Report ({self.report_type}) by {self.user.username} on {self.generated_at}"
