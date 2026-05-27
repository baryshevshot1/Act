# apps.core.rls — единственный package, которому разрешён прямой connection.cursor()
# и raw SQL через .raw() / RunSQL (см. .importlinter CONTRACT 0).
# Содержит RLS middleware (SET LOCAL app.current_user_id) и helper-функции
# для управления GUC внутри transaction.atomic().
