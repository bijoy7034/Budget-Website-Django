from rest_framework import serializers
from ...models import GroupChat, GroupChatMessage, IncomeSource, Income, Category, Expense, FinancialGoals, Group, GroupExpense, GroupFinancialGoal, GroupMember, GroupExpenseContribution, FinancialGoalContribution, Budget, BillReminder
from datetime import date
from django.contrib.auth.models import User

class IncomeSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeSource
        fields = ['id', 'source_name', 'created_at', 'updated_at'] 
        read_only_fields = ['created_at', 'updated_at']

class IncomeSerializer(serializers.ModelSerializer):
    source = serializers.PrimaryKeyRelatedField(queryset=IncomeSource.objects.all())

    class Meta:
        model = Income
        fields = ['id', 'user', 'source', 'amount', 'description', 'date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['source'] = IncomeSourceSerializer(instance.source).data  # Correctly reference 'source'
        return representation


class CatagorySerilaizer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at', 'user']
        read_only_fields = ['created_at', 'updated_at',  'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ExpenseSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Expense
        fields = ['id', 'user', 'category', 'amount', 'description', 'date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['category'] = CatagorySerilaizer(instance.category).data
        return representation


class TransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()  
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField()
    date = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

class ManualContributionSerializer(serializers.Serializer):
    goal_id = serializers.IntegerField() 
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)  

    def validate(self, attrs):
        if attrs['amount'] <= 0:
            raise serializers.ValidationError("The amount must be greater than zero.")
        return attrs

class FinancialGoalContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialGoalContribution
        fields = ['id', 'goal', 'user', 'amount', 'date']
        read_only_fields = ['id', 'goal', 'user', 'date']


class FinancialGoalSerializer(serializers.ModelSerializer):
    contributions = ManualContributionSerializer(many=True, read_only=True)

    class Meta:
        model = FinancialGoals
        fields = [
            'id', 'user', 'name', 'description', 
            'target_amount', 'current_amount', 'allocated_amount', 
            'target_date', 'recurrence', 'income_source', 
            'created_at', 'updated_at', 'contributions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'contributions']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    # No changes needed for the validate method here

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Retrieve contributions from the FinancialGoalContribution model
        representation['contributions'] = FinancialGoalContributionSerializer(instance.contributions.all(), many=True).data
        return representation



class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

    def save(self, group):
        username = self.validated_data['username']
        user = User.objects.get(username=username)

        if GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError("User is already a member of this group.")
        
        GroupMember.objects.create(group=group, user=user)



class GroupMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')  # Fetching username from the related user

    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'username', 'joined_at']  # Include user ID, username, and joined_at fields
class GroupExpenseSerializer(serializers.ModelSerializer):
    contributions = serializers.SerializerMethodField()

    class Meta:
        model = GroupExpense
        fields = ['id', 'group', 'user', 'title', 'amount', 'description', 'date', 'contributions']
        read_only_fields = ['user']

    def get_contributions(self, obj):
        contributions = obj.contributions.all()
        return GroupExpenseContributionSerializer(contributions, many=True).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Example: Add a custom field for total contributions
        representation['total_contributions'] = sum(contrib.amount for contrib in instance.contributions.all())
        return representation


# Serializer for Group
class GroupSerializer(serializers.ModelSerializer):
    members = GroupMemberSerializer(many=True, read_only=True)  # Serialize the members, including their username
    expenses = GroupExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'admin', 'members', 'expenses']
        read_only_fields = ['id', 'created_at', 'updated_at', 'admin', 'expenses']

    def create(self, validated_data):
        user = self.context['request'].user  # Get the logged-in user (admin)
        group = Group.objects.create(admin=user, **validated_data)  # Create the group instance
        # Automatically create a GroupMember entry for the admin
        GroupMember.objects.create(group=group, user=user)  # Add the admin as the first member
        return group

    def to_representation(self, instance):
        """
        Override the to_representation method to customize how the members are represented.
        This will ensure that the admin's username and all the group members' usernames are included in the response.
        """
        representation = super().to_representation(instance)
        
        # Custom representation for members
        members_data = []
        for member in instance.members.all():
            member_data = {
                'id': member.id,
                'username': member.user.username,  # Get the username from the related User model
                'joined_at': member.joined_at
            }
            members_data.append(member_data)
        
        # Add the custom members data to the representation
        representation['members'] = members_data
        
        # Replace the admin field with the admin's username
        representation['admin'] = instance.admin.username  # Replace admin ID with username
        
        return representation

class GroupExpenseContributionSerializer(serializers.ModelSerializer):
    expense_id = serializers.IntegerField(write_only=True)
    group_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GroupExpenseContribution
        fields = ['id', 'expense_id', 'group_id', 'amount', 'date', 'user']
        read_only_fields = ['user']

    def create(self, validated_data):
        expense_id = validated_data.pop('expense_id')
        group_id = validated_data.pop('group_id')

        # Fetch the GroupExpense instance
        group_expense = GroupExpense.objects.get(id=expense_id, group_id=group_id)

        # Create the contribution
        contribution = GroupExpenseContribution.objects.create(
            group_expense=group_expense,
            user=self.context['request'].user,
            **validated_data
        )
        return contribution



class GroupFinancialGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupFinancialGoal
        fields = ['id', 'group', 'name', 'target_amount', 'current_amount', 'target_date', 'created_at', 'updated_at', 'user']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class GroupChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupChat
        fields = ['id', 'group', 'created_at', 'updated_at']
        read_only_fields = ['id',  'created_at', 'updated_at']


class GroupChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupChatMessage
        fields = ['id', 'group_chat','user', 'message', 'created_at', 'updated_at']
        read_only_fields = ['id','group_chat', 'created_at', 'updated_at', 'user']

class BudgetSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    is_over_budget = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = ['id', 'name', 'description', 'period', 'budget_limit', 'total_income', 'total_expenses', 'balance', 'is_over_budget', 'created_at', 'updated_at', 'last_reset_date']
        read_only_fields = ['user', 'balance', 'is_over_budget', 'last_reset_date'] 

    def get_balance(self, obj):
        return obj.calculate_balance()

    def get_is_over_budget(self, obj):
        return obj.is_over_budget()

    

class BillReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillReminder
        fields = ['id', 'bill_name', 'amount', 'category', 'due_date', 'recurring_interval', 'reminder_time', 'user', 'is_paid', 'payment_date']
        read_only_fields = ['id', 'user']

    def update(self, instance, validated_data):
        """
        Override the update method to handle the case where the bill is being marked as paid
        and create a new recurring bill if necessary.
        """
        if 'is_paid' in validated_data and validated_data['is_paid']:
            # Mark the bill as paid
            instance.is_paid = True
            instance.payment_date = validated_data.get('payment_date', instance.payment_date)
            instance.save()

            # If it's a recurring bill, create the next bill
            if instance.recurring_interval and instance.recurring_interval != 'one_time':
                new_due_date = self.get_next_due_date(instance)
                BillReminder.objects.create(
                    bill_name=instance.bill_name,
                    amount=instance.amount,
                    category=instance.category,
                    due_date=new_due_date,
                    recurring_interval=instance.recurring_interval,
                    reminder_time=instance.reminder_time,
                    user=instance.user,
                    is_paid=False  # New bill should not be paid
                )

        return super().update(instance, validated_data)

    def get_next_due_date(self, instance):
        """
        Helper method to calculate the next due date based on the recurring interval.
        """
        from datetime import timedelta
        import calendar

        due_date = instance.due_date

        if instance.recurring_interval == 'monthly':
            # Move the date to the same day next month
            next_month = due_date.replace(month=due_date.month % 12 + 1)
            return next_month
        elif instance.recurring_interval == 'weekly':
            return due_date + timedelta(weeks=1)
        elif instance.recurring_interval == 'yearly':
            # Add one year to the due date
            next_year = due_date.replace(year=due_date.year + 1)
            return next_year
        # Add more logic for other intervals if needed
        return due_date
