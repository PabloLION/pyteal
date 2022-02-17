from typing import cast, TYPE_CHECKING, Union

from ..types import TealType
from ..config import NUM_SLOTS
from ..errors import TealInputError, TealInternalError
from .expr import Expr

if TYPE_CHECKING:
    from ..compiler import CompileOptions


# class Slot:
#     """Abstract base closs for ScratchSlot and DynamicSlot"""

#     def __init__(self):
#         self.id: Union[int, Expr] = None
#         self.isReservedSlot: bool = None

#     def store(self, value: Expr = None) -> Expr:
#         """Get an expression to store a value in this slot.

#         Args:
#             value (optional): The value to store in this slot. If not included, the last value on
#             the stack will be stored. NOTE: storing the last value on the stack breaks the typical
#             semantics of PyTeal, only use if you know what you're doing.
#         """
#         if value is not None:
#             return ScratchStore(self, value)

#         if not isinstance(self, ScratchSlot):
#             raise TealInternalError(
#                 "ScratchStackStore is only setup to handle ScratchSlot's but was about to supply type {}".format(
#                     type(self)
#                 )
#             )

#         return ScratchStackStore(cast(ScratchSlot, self))

#     def load(self, type: TealType = TealType.anytype) -> "ScratchLoad":
#         """Get an expression to load a value from this slot.

#         Args:
#             type (optional): The type being loaded from this slot, if known. Defaults to
#                 TealType.anytype.
#         """
#         return ScratchLoad(self, type)

#     def index(self) -> "ScratchIndex":
#         return ScratchIndex(self)

#     def __hash__(self):
#         return hash(self.id)


# Slot.__module__ = "pyteal"


class ScratchSlot:
    """Represents the allocation of a scratch space slot."""

    # Unique identifier for the compiler to automatically assign slots
    # The id field is used by the compiler to map to an actual slot in the source code
    # Slot ids under 256 are manually reserved slots
    nextSlotId = NUM_SLOTS

    # def __init__(self):
    #     self.id: Union[int, Expr] = None
    #     self.isReservedSlot: bool = None
    def __init__(self, requestedSlotId: int = None):
        """Initializes a scratch slot with a particular id

        Args:
            requestedSlotId (optional): A scratch slot id that the compiler must store the value.
            This id may be a Python int in the range [0-256).
        """
        # super().__init__()

        if requestedSlotId is None:
            self.id = ScratchSlot.nextSlotId
            ScratchSlot.nextSlotId += 1
            self.isReservedSlot = False
        else:
            if requestedSlotId < 0 or requestedSlotId >= NUM_SLOTS:
                raise TealInputError(
                    "Invalid slot ID {}, shoud be in [0, {})".format(
                        requestedSlotId, NUM_SLOTS
                    )
                )
            self.id = requestedSlotId
            self.isReservedSlot = True

    def store(self, value: Expr = None) -> Expr:
        """Get an expression to store a value in this slot.

        Args:
            value (optional): The value to store in this slot. If not included, the last value on
            the stack will be stored. NOTE: storing the last value on the stack breaks the typical
            semantics of PyTeal, only use if you know what you're doing.
        """
        if value is not None:
            return ScratchStore(self, value)

        if not isinstance(self, ScratchSlot):
            raise TealInternalError(
                "ScratchStackStore is only setup to handle ScratchSlot's but was about to supply type {}".format(
                    type(self)
                )
            )

        return ScratchStackStore(cast(ScratchSlot, self))

    def load(self, type: TealType = TealType.anytype) -> "ScratchLoad":
        """Get an expression to load a value from this slot.

        Args:
            type (optional): The type being loaded from this slot, if known. Defaults to
                TealType.anytype.
        """
        return ScratchLoad(self, type)

    def index(self) -> "ScratchIndex":
        return ScratchIndex(self)

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return "ScratchSlot({})".format(self.id)

    def __str__(self):
        return "slot#{}".format(self.id)


ScratchSlot.__module__ = "pyteal"


# class DynamicSlot(Slot):
#     """Represents the allocation of a scratch space slot."""

#     # Unique identifier for the compiler to automatically assign slots
#     # The id field is used by the compiler to map to an actual slot in the source code
#     # Slot ids under 256 are manually reserved slots
#     nextSlotId = NUM_SLOTS

#     def __init__(self, slotExpr: Expr):
#         """Initializes a scratch slot with a particular id

#         Args:
#             requestedSlotId (optional): A scratch slot id that the compiler must store the value.
#             This id may be a Python int in the range [0-256).
#         """
#         super().__init__()

#         # TODO: Zeph to add assertions
#         self.id = slotExpr
#         self.isReservedSlot = False

#     def __repr__(self):
#         return "DynamicSlot({})".format(self.id)

#     def __str__(self):
#         return "dslot#{}".format(self.id)


# DynamicSlot.__module__ = "pyteal"


class ScratchIndex(Expr):
    def __init__(self, slot: ScratchSlot):
        super().__init__()
        self.slot = slot

    def __str__(self):
        return "(ScratchIndex {})".format(self.slot)

    def __hash__(self):
        return hash(self.slot.id)

    def type_of(self):
        return TealType.uint64

    def has_return(self):
        return False

    def __teal__(self, options: "CompileOptions"):
        from ..ir import TealOp, Op, TealBlock

        op = TealOp(self, Op.int, self.slot)
        return TealBlock.FromOp(options, op)


ScratchIndex.__module__ = "pyteal"


class ScratchLoad(Expr):
    """Expression to load a value from scratch space."""

    def __init__(
        self,
        slot: ScratchSlot,
        type: TealType = TealType.anytype,
        index_expression: Expr = None,
    ):
        """Create a new ScratchLoad expression.

        Args:
            slot: The slot to load the value from.
            type (optional): The type being loaded from this slot, if known. Defaults to
                TealType.anytype.
        """
        super().__init__()

        if (slot is None) == (index_expression is None):
            raise TealInternalError(
                "Exactly one of slot or index_expressions must be provided"
            )

        self.slot = slot
        self.type = type
        self.index_expression = index_expression

    def __str__(self):
        return "(Load {})".format(self.slot)

    def __teal__(self, options: "CompileOptions"):
        from ..ir import TealOp, Op, TealBlock

        if self.index_expression is not None:
            op = TealOp(self, Op.loads)
            return TealBlock.FromOp(options, op, self.index_expression)

        if not isinstance(self.slot, ScratchSlot):
            raise TealInternalError(
                "cannot handle slot of type {}".format(type(self.slot))
            )
        op = TealOp(self, Op.load, self.slot)
        return TealBlock.FromOp(options, op)

        # if not isinstance(self.slot, DynamicSlot):
        #     raise TealInternalError("unrecognized slot type {}".format(type(self.slot)))

        # op = TealOp(self, Op.loads)
        # return TealBlock.FromOp(options, op, cast(Expr, self.slot.id))

    def type_of(self):
        return self.type

    def has_return(self):
        return False


ScratchLoad.__module__ = "pyteal"


class ScratchStore(Expr):
    """Expression to store a value in scratch space."""

    def __init__(self, slot: ScratchSlot, value: Expr, index_expression: Expr = None):
        """Create a new ScratchStore expression.

        Args:
            slot: The slot to store the value in.
            value: The value to store.
        """
        super().__init__()

        if (slot is None) == (index_expression is None):
            raise TealInternalError(
                "Exactly one of slot or index_expressions must be provided"
            )

        self.slot = slot
        self.value = value
        self.index_expression = index_expression

    def __str__(self):
        return "(Store {} {})".format(self.slot, self.value)

    def __teal__(self, options: "CompileOptions"):
        from ..ir import TealOp, Op, TealBlock

        if self.index_expression is not None:
            op = TealOp(self, Op.stores)
            return TealBlock.FromOp(options, op, self.index_expression, self.value)

        if not isinstance(self.slot, ScratchSlot):
            raise TealInternalError(
                "cannot handle slot of type {}".format(type(self.slot))
            )
        op = TealOp(self, Op.store, self.slot)
        return TealBlock.FromOp(options, op, self.value)

        # if not isinstance(self.slot, DynamicSlot):
        #     raise TealInternalError("unrecognized slot type {}".format(type(self.slot)))

        # op = TealOp(self, Op.stores)
        # return TealBlock.FromOp(options, op, cast(Expr, self.slot.id), self.value)

    def type_of(self):
        return TealType.none

    def has_return(self):
        return False


ScratchStore.__module__ = "pyteal"


class ScratchStackStore(Expr):
    """Expression to store a value from the stack in scratch space.

    NOTE: This expression breaks the typical semantics of PyTeal, only use if you know what you're
    doing.
    """

    def __init__(self, slot: ScratchSlot):
        """Create a new ScratchStackStore expression.

        Args:
            slot: The slot to store the value in.
        """
        super().__init__()

        self.slot = slot

    def __str__(self):
        return "(ScratchStackStore {})".format(self.slot)

    def __teal__(self, options: "CompileOptions"):
        from ..ir import TealOp, Op, TealBlock

        op = TealOp(self, Op.store, cast(ScratchSlot, self.slot))
        return TealBlock.FromOp(options, op)

    def type_of(self):
        return TealType.none

    def has_return(self):
        return False


ScratchStackStore.__module__ = "pyteal"
