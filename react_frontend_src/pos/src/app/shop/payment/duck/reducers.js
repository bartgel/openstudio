import T from './types'

export const shopPaymentReducer = (state = {}, action={ type: null }) => {
    switch (action.type) {
        case T.SET_SELECTED_PAYMENT_METHOD:
            return {
                ...state,
                selectedID: action.data
            }
        case T.CLEAR_SELECTED_PAYMENT_METHOD:
            return {
                ...state,
                selectedID: ""
            }
        default:
            return {
                ...state
            }
    }
}
