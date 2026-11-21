from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant_all", "0007_dishrating"),
    ]

    operations = [
        migrations.AddField(
            model_name="dishrating",
            name="comment",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="dishrating",
            name="score",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
